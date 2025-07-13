# offer_workflow.py

import os
import json
from dotenv import load_dotenv

# Import configurations
import prompts_config as pc
from config_data import (
    INTERNAL_HOURLY_RATES, TYPICAL_SERVICE_AREAS, calculate_position_price, DATA_DIR,
    BEXIO_API_TOKEN # Import BEXIO_API_TOKEN to check if it's set for Bexio integration
)
from llm_utils import get_llm_response, get_llm_json_response
from vector_store_utils import load_and_vectorize_offers, retrieve_context
from research_utils import ask_for_external_research, perform_client_research, perform_offer_focused_research
from bexio_utils import transform_to_bexio_format, create_bexio_quote # For Bexio integration

# --- CONFIGURATION ---
load_dotenv()

# --- HELPER FUNCTIONS ---
def request_positions_manually_from_consultant(num_positions_str):
    """
    Handles manual input for offer positions if AI suggestion is not used or needs full replacement.
    This function will likely need adjustment if text positions also need manual input,
    or it could be deprecated if the (c)hange flow is robust enough.
    For now, it focuses on "Offer Position" like details.
    """
    manual_positions = []
    num_positions = 0
    if num_positions_str.isdigit() and int(num_positions_str) > 0:
        num_positions = int(num_positions_str)
    else:
        print("Invalid number of positions. Defaulting to 1 Offer Position.")
        num_positions = 1

    if num_positions > 0:
        print(f"\nPlease define details for {num_positions} position(s) manually.")
        for i in range(num_positions):
            position_detail = {"type": "Offer Position"} # Defaulting to Offer Position
            print(f"\n--- Details for Manual Position {i+1} ---")
            position_detail["proposed_title"] = input("  Title/Focus for this Position: ")
            position_detail["focus_description"] = input("  Key points/Brief description for this Position: ")
            
            # Ask if it's a Text Position or Offer Position
            while True:
                ptype = input("  Is this a (t)ext position or an (o)ffer position? [t/o]: ").lower()
                if ptype == 't':
                    position_detail["type"] = "Text Position"
                    # For text positions, we might not need service area or hours
                    position_detail.pop("estimated_hours_suggestion", None)
                    position_detail.pop("suggested_service_area", None)
                    break
                elif ptype == 'o':
                    position_detail["type"] = "Offer Position"
                    while True:
                        sa_input = input(f"  Service Area (Options: {', '.join(TYPICAL_SERVICE_AREAS)}): ")
                        if sa_input in TYPICAL_SERVICE_AREAS:
                            position_detail["suggested_service_area"] = sa_input
                            break
                        else:
                            print(f"  Invalid service area. Please choose from list.")
                    while True:
                        try:
                            hours_val = float(input("  Your estimated hours for this Position: "))
                            if hours_val > 0:
                                position_detail["estimated_hours_suggestion"] = hours_val
                                break
                            else:
                                print("  Hours must be a positive number.")
                        except ValueError:
                            print("  Please enter a valid number for hours.")
                    break
                else:
                    print("Invalid input. Please enter 't' or 'o'.")
            
            # Price calculation only for Offer Positions
            if position_detail["type"] == "Offer Position":
                price_info = calculate_position_price(
                    position_detail["suggested_service_area"],
                    position_detail["estimated_hours_suggestion"]
                )
                # Storing calculated price info, though it's not part of the final JSON structure per se,
                # it's useful context for the consultant during this manual step.
                position_detail["calculated_price_info"] = price_info
            manual_positions.append(position_detail)
    return manual_positions


def initial_chat_to_gather_high_level_info():
    print("\n--- Starting Offer Information Gathering Chat (High-Level) ---")
    gathered_info = {}
    questions = [
        "What is the name of the client (or a placeholder for the PoC)?",
        "What is the client's business/industry?",
        "What is the main objective or title for this offer/project? (This will be used as 'project_title')",
        "Can you briefly describe the key services or overall deliverables the client needs?",
        "Are there any specific project focus areas or keywords we should prioritize?",
        "Roughly, how many main service components or phases (including text sections) do you think this offer might involve?",
        "Which language should the offer be in? (German/English)",
        "Do you have any additional context? (e.g., meeting notes, email history, ...)",
    ]
    question_keys = [
        "client_name", "client_industry", "project_title",
        "key_services_description", "project_focus_tags_input",
        "estimated_num_components", "language", "additional_context"
    ]

    for i, q_text in enumerate(questions):
        print(f"\nAI: {q_text}")
        user_response = input("You: ")
        # Ensure estimated_num_components is always an int, but store as string for consistency
        if question_keys[i] == "estimated_num_components":
            try:
                user_response = str(int(user_response))
            except Exception:
                user_response = "1"
        gathered_info[question_keys[i]] = user_response

    print("\n--- High-Level Information Gathering Complete ---")
    return gathered_info

def display_proposed_structure(proposed_structure_json):
    print("\nAI Suggestion for Offer Structure:")
    for i, pos_suggestion in enumerate(proposed_structure_json):
        print(f"  Position {i+1} ({pos_suggestion.get('type', 'N/A')}):")
        print(f"    Title: {pos_suggestion.get('proposed_title', 'N/A')}")
        print(f"    Focus: {pos_suggestion.get('focus_description', 'N/A')}")
        if pos_suggestion.get('type') == "Offer Position":
            print(f"    Suggested Hours: {pos_suggestion.get('estimated_hours_suggestion', 'N/A')}")
            print(f"    Suggested Service Area: {pos_suggestion.get('suggested_service_area', 'N/A')}")

def propose_offer_structure_and_get_confirmation(high_level_info, retrieved_contexts, client_research_summary, offer_focused_research_summary):
    user_feedback_for_structure_change = "" # Initialize feedback
    current_proposed_structure = []

    while True: # Loop for (r)estart / (c)hange / (a)ccept
        print("\n--- AI Proposing Offer Structure ---")
        context_str = "\n\n---\n\n".join([
            f"Context from Past Offer (ID: {ctx.get('offer_id', 'N/A')}, Position: {ctx.get('position_title', 'N/A')}):\n{ctx['content']}"
            for ctx in retrieved_contexts
        ]) if retrieved_contexts else "No specific past offer context was retrieved."

        details_summary = "\n".join([f"- {key.replace('_', ' ').capitalize()}: {value}" for key, value in high_level_info.items() if key not in ["client_research_summary", "offer_focused_research_summary"]])

        system_prompt_for_proposal = pc.PROMPT_PROPOSE_STRUCTURE_SYSTEM_TEMPLATE.format(
            typical_service_areas_list_str=', '.join(TYPICAL_SERVICE_AREAS)
        )
        
        user_feedback_prompt_segment = ""
        if user_feedback_for_structure_change:
            user_feedback_prompt_segment = f"\nUser Feedback for Changes:\n---\n{user_feedback_for_structure_change}\n---\nPlease incorporate this feedback into your new proposal."

        user_prompt_for_proposal = pc.PROMPT_PROPOSE_STRUCTURE_USER_TEMPLATE.format(
            details_summary=details_summary,
            context_str=context_str,
            client_research_summary=client_research_summary,
            offer_focused_research_summary=offer_focused_research_summary,
            user_feedback_for_structure_change_prompt_segment=user_feedback_prompt_segment
        )

        print("AI is thinking about the offer structure...")
        proposed_structure_json = get_llm_json_response(
            system_prompt=system_prompt_for_proposal,
            user_prompt=user_prompt_for_proposal
        )

        if "error" in proposed_structure_json or not isinstance(proposed_structure_json, list):
            print("AI failed to propose a valid structure. You can try to (r)estart or define manually.")
        else:
            current_proposed_structure = proposed_structure_json # Store current valid proposal
            display_proposed_structure(current_proposed_structure)

        print("\n--- Consultant Review & Confirmation ---")
        action = input("Do you want to (a)ccept this structure, (c)hange it (provide feedback), or (r)estart proposal from scratch? [a/c/r]: ").lower()

        if action == 'a':
            if not current_proposed_structure:
                print("No structure to accept. Please try (r)estart.")
                continue
            confirmed_positions = []
            for pos in current_proposed_structure:
                confirmed_pos = {
                    "type": pos.get("type"),
                    "title_input": pos.get("proposed_title"),
                    "description_input": pos.get("focus_description")
                }
                if pos.get("type") == "Offer Position":
                    confirmed_pos["service_area_input"] = pos.get("suggested_service_area")
                    confirmed_pos["service_area_input"] = pos.get("suggested_service_area", TYPICAL_SERVICE_AREAS[0])
                    try:
                        hours = float(pos.get('estimated_hours_suggestion', 1))
                        if hours <= 0: hours = 1
                        confirmed_pos["hours_input"] = hours
                    except (ValueError, TypeError):
                        print(f"Warning: Invalid hours for '{pos.get('proposed_title')}'. Defaulting to 1.")
                        confirmed_pos["hours_input"] = 1.0
                    price_info = calculate_position_price(
                        confirmed_pos["service_area_input"],
                        float(confirmed_pos["hours_input"])
                    )
                    confirmed_pos["calculated_price_info"] = price_info
                confirmed_positions.append(confirmed_pos)
            # --- Always append Abgrenzung/Terms and Conditions as a Text Position ---
            abgr_de = (
                "Wenn nicht explizit anders definiert, gilt f&uuml;r alle Positionen:<br />"
                "<ul>"
                "<li>Kosten von Drittanbietern sind nicht Bestandteil und werden vom Kunden &uuml;bernommen</li>"
                "<li>Als Basis f&uuml;r eine Zusammenarbeit ist das Digital Horizon Support Abo Voraussetzung (Ausnahme einzelne Workshops und Kurzprojekte)</li>"
                "<li>Abonnemente starten am Zusagedatum und werden direkt im Voraus in Rechnung gestellt</li>"
                "<li>Abonnemente erneuern sich ohne Gegenbericht automatisch. R&uuml;ckerstattungen bei K&uuml;ndigung innerhalb einer laufenden Periode sind nur in Ausnahmef&auml;llen m&ouml;glich</li>"
                "<li>Bildmaterial, Videos, Texte und andere Medien werden durch den Kunden angeliefert, ausser die Erstellung ist Teil der Offerte</li>"
                "<li>Abkl&auml;rungen, &Uuml;bergaben, Besprechungen, Einf&uuml;hrungen und Abnahmen finden remote statt (Telefon, Bildschirm&uuml;bertragung, E-Mail etc.)</li>"
                "<li>Workshops, Meetings oder Schulungen in Person finden an einem Sidekick Standort statt</li>"
                "<li>Ist ein Vor-Ort Termin gew&uuml;nscht, so werden Anfahrtszeit zum Stundensatz und Fahrtkosten verrechnet</li>"
                "<li>Bestehende Zug&auml;nge oder Freigaben zu Plattformen werden von Kunde an Sidekicks weitergegeben</li>"
                "<li>Entscheidet der Kunde bei der Abnahme einer Leistung, wie etwa einer Kampagne, diese nicht zu publizieren, aktivieren oder verschicken, so wird die Position trotzdem verrechnet</li>"
                "<li>Falls von einer Plattform ein Zahlungsmittel ben&ouml;tigt wird, hinterlegt der Kunde seine eigene Firmenkreditkarte</li>"
                "<li>Der Kunde ist verpflichtet, seine Finanzen im Zusammenhang mit den Dienstleistungen der Your Sidekicks AG sorgf&auml;ltig zu &uuml;berwachen, einschliesslich der Kontrolle von Werbebudgetausgaben, und Unstimmigkeiten umgehend zu melden. Sidekicks haftet nicht f&uuml;r finanzielle Verluste bei Mediabudgetausgaben.&nbsp;</li>"
                "<li>Sidekicks haftet nicht f&uuml;r Drittanbieter-Tools, die im Rahmen der Dienstleistung verwendet werden, auch wenn die Toolkosten via Sidekicks getragen werden.&nbsp;</li>"
                "<li>Auch wenn eine Plattform eine Kampagne, Zielgruppe oder Inhalt unerwartet ablehnen sollte, wird die zugeh&ouml;rige Position verrechnet</li>"
                "<li>Der Kunde hat die Offertenpunkte und zugeh&ouml;rigen Informationen genau zu pr&uuml;fen, bei Unklarheiten nachzufragen und akzeptiert diese mit der Zusage als Pauschalpreise</li>"
                "<li>Die Rechnungserstellung erfolgt nach der ersten &Uuml;bergabe der Arbeitsergebnisse f&uuml;r alle Positionen gleichzeitig&nbsp;</li>"
                "<li>Es gelten die Allgemeine Gesch&auml;ftsbedingungen (AGB) sowie die Datenschutzerkl&auml;rung von Your Sidekicks AG einsehbar unter&nbsp;www.sidekicks.ch</li>"
                "</ul>"
            )
            abgr_en = (
                "Unless explicitly defined otherwise, the following applies to all positions:<br />"
                "<ul>"
                "<li>Costs incurred from third-party services are not included and will be covered by the customer.</li>"
                "<li>The Digital Horizon Support subscription is a prerequisite for collaboration (except for individual workshops and short-term projects).</li>"
                "<li>Subscriptions start from the date of confirmation and are billed in advance.</li>"
                "<li>Subscriptions renew automatically unless notified otherwise. Refunds for cancellations within a current period are only possible in exceptional circumstances.</li>"
                "<li>Visuals, videos, texts, and other media are to be provided by the customer, unless their creation is included in the offer.</li>"
                "<li>Clarifications, handovers, meetings, introductions, and acceptances will be conducted remotely (via phone, screen sharing, email, etc.).</li>"
                "<li>Workshops, meetings, or training sessions in person will take place at a Sidekick location.</li>"
                "<li>If an on-site meeting is requested, travel time will be billed at the hourly rate, along with travel expenses.</li>"
                "<li>Existing access or permissions to platforms will be transferred from the customer to Sidekicks.</li>"
                "<li>If the customer decides not to publish, activate, or distribute a service upon acceptance, such as a campaign, the position will still be invoiced.</li>"
                "<li>If a platform requires payment, the customer must provide their own corporate credit card.</li>"
                "<li>The customer is responsible for monitoring their finances related to Your Sidekicks AG's services, including advertising budget expenditures, and reporting any discrepancies promptly. Sidekicks is not liable for financial losses incurred from media budget expenditures.</li>"
                "<li>Sidekicks is not liable for third-party tools used within the scope of the service, even if the tool costs are covered by Sidekicks.</li>"
                "<li>Even if a platform unexpectedly rejects a campaign, target audience, or content, the associated position will still be invoiced.</li>"
                "<li>The customer is responsible for carefully reviewing the offer points and associated information, seeking clarification if needed, and accepting them as fixed prices upon confirmation.</li>"
                "<li>Invoicing will occur after the initial handover of work results for all positions simultaneously.</li>"
                "<li>The General Terms and Conditions (GTC) and the privacy policy of Your Sidekicks AG apply, accessible at www.sidekicks.ch.</li>"
                "</ul>"
            )
            lang = high_level_info.get("language", "German").lower()
            if "en" in lang:
                abgr_text = abgr_en
                abgr_title = "Terms and Conditions"
            elif "de" in lang or "ger" in lang:
                abgr_text = abgr_de
                abgr_title = "Abgrenzung"
            else:
                abgr_text = abgr_en + "<br /><br />" + abgr_de
                abgr_title = "Terms and Conditions / Abgrenzung"
            confirmed_positions.append({
                "type": "Text Position",
                "title_input": abgr_title,
                "description_input": abgr_text
            })
            high_level_info["positions_details"] = confirmed_positions
            print("\n--- Offer Structure Confirmed by Consultant ---")
            return high_level_info # Return the whole high_level_info dict
        elif action == 'c':
            if not current_proposed_structure:
                print("No structure to change. Please try (r)estart first.")
                continue
            user_feedback_for_structure_change = input("Please describe the changes you'd like for the offer structure (e.g., 'add a text position about our methodology after the intro', 'combine the first two offer positions', 'make the third position a text position instead'):\n")
            continue 
        elif action == 'r':
            user_feedback_for_structure_change = "" # Reset feedback for a clean restart
            current_proposed_structure = [] # Reset current proposal
            print("Restarting structure proposal...")
            continue
        else:
            print("Invalid option. Please choose 'a', 'c', or 'r'.")


def construct_final_drafting_prompts(final_offer_details_dict, retrieved_contexts, client_research_summary, offer_focused_research_summary):
    # final_offer_details_dict now IS high_level_info, including 'project_title' and 'positions_details'
    
    overall_offer_summary = f"""
Project Title: {final_offer_details_dict.get('project_title', 'N/A')}
Client Name: {final_offer_details_dict.get('client_name', 'N/A')}
Client Industry: {final_offer_details_dict.get('client_industry', 'N/A')}
Key Services Overview: {final_offer_details_dict.get('key_services_description', 'N/A')}
"""
    # Project Focus Tags might be less relevant now, or handled differently
    # Project Focus Tags: {final_offer_details_dict.get('project_focus_tags_input', 'N/A')} 

    positions_to_draft_info_str = ""
    # This is the list of confirmed structures (type, title, focus_description, optionally hours/service_area)
    confirmed_structure_list = final_offer_details_dict.get("positions_details", [])

    if confirmed_structure_list:
        temp_list = []
        for i, pos_struct in enumerate(confirmed_structure_list):
            pos_type = pos_struct.get('type', 'Offer Position') # Default to offer if somehow missing
            entry = f"Confirmed Position {i+1} (Type: {pos_type}):\n"
            entry += f"  - Title: {pos_struct.get('title_input', 'N/A')}\n"
            entry += f"  - Key Focus/Description Points for AI to expand: {pos_struct.get('description_input', 'N/A')}\n"
            if pos_type == "Offer Position":
                entry += f"  - Consultant Confirmed Service Area: {pos_struct.get('service_area_input', 'N/A')}\n"
                entry += f"  - Consultant Confirmed Estimated Hours: {pos_struct.get('hours_input', 'N/A')}\n"
                # Now include the calculated price details for the LLM to use
                price_info = pos_struct.get("calculated_price_info", {})
                if "error" not in price_info and price_info:
                    entry += f"  - Hourly Rate (CHF): {price_info.get('hourly_rate_chf', 'N/A')}\n"
                    entry += f"  - Service Area Used for Pricing: {price_info.get('service_area_used', 'N/A')}\n"
                    entry += f"  - Calculated Price (CHF) for this position: {price_info.get('calculated_price_chf', 'N/A')}\n"
                else:
                    entry += "  - Pricing Information: Not available or error in calculation.\n"
            temp_list.append(entry)
        positions_to_draft_info_str = "\n\n".join(temp_list)
    else:
        positions_to_draft_info_str = "No specific positions were confirmed. Draft a general offer based on 'Key Services Overview'."

    context_str = "\n\n---\n\n".join([
        f"Context from Past Offer (ID: {ctx.get('offer_id', 'N/A')}, Position: {ctx.get('position_title', 'N/A')}):\n{ctx['content']}"
        for ctx in retrieved_contexts
    ]) if retrieved_contexts else "No specific past offer context was retrieved."

    # The output_instruction needs to align with the new top-level JSON object structure
    output_instruction = (
        "Ensure your output is a single valid JSON object. "
        "This object must have a top-level string field 'project_title' and a top-level array field 'positions'. "
        "Each item in the 'positions' array must follow the schema described, including an integer 'position_id' and correct 'type'. "
        "For 'Offer Position' types, the 'description' MUST be a bullet-point list. "
        "For 'Text Position' types, the 'description' should be a paragraph."
    )
    
    system_prompt = pc.PROMPT_DRAFT_JSON_SYSTEM
    user_prompt = pc.PROMPT_DRAFT_JSON_USER_TEMPLATE.format(
        overall_offer_summary=overall_offer_summary, # Contains project_title
        positions_to_draft_info_str=positions_to_draft_info_str,
        context_str=context_str,
        output_instruction=output_instruction,
        json_schema_description_text=pc.PROMPT_DRAFT_JSON_SCHEMA_DESCRIPTION, # This schema was updated
        client_research_summary=client_research_summary,
        offer_focused_research_summary=offer_focused_research_summary
    )

    print("\n--- Constructing Final JSON Drafting Prompts (for LLM) ---")
    # print(f"System Prompt for Final Draft: {system_prompt}") # For debugging
    # print(f"User Prompt for Final Draft: {user_prompt}") # For debugging
    return system_prompt, user_prompt

# --- MAIN WORKFLOW FUNCTION ---
def main():
    print("Starting Sidekicks AI Offer Assistant PoC (Interactive Mode with Review Step)...")

    load_and_vectorize_offers(DATA_DIR)

    # project_title is now gathered here
    high_level_offer_info = initial_chat_to_gather_high_level_info() 

    client_research_summary = "No client research performed."
    offer_focused_research_summary = "No offer-focused research performed."

    if ask_for_external_research():
        print("\n--- External Research Process Initiated ---")
        client_name_for_research = high_level_offer_info.get("client_name", "Unknown Client")
        client_industry_for_research = high_level_offer_info.get("client_industry", "Unknown Industry")
        client_research_summary = perform_client_research(client_name_for_research, client_industry_for_research)

        project_desc_for_research = high_level_offer_info.get("key_services_description", "General Offer Focus")
        project_focus_for_research = high_level_offer_info.get("project_focus_tags_input", "General") # May deprecate this tag usage
        offer_focused_research_summary = perform_offer_focused_research(project_desc_for_research, project_focus_for_research)

        # Store summaries directly in high_level_offer_info for easier access
        high_level_offer_info["client_research_summary"] = client_research_summary
        high_level_offer_info["offer_focused_research_summary"] = offer_focused_research_summary
        print("--- External Research Process Completed ---")
    else:
        print("\n--- Skipping External Research ---")
        high_level_offer_info["client_research_summary"] = client_research_summary
        high_level_offer_info["offer_focused_research_summary"] = offer_focused_research_summary
    
    rag_query_overall = f"Offer for {high_level_offer_info.get('client_industry', '')} client: {high_level_offer_info.get('project_title', '')}, focusing on {high_level_offer_info.get('project_focus_tags_input', '')} and services like {high_level_offer_info.get('key_services_description', '')}"
    retrieved_contexts_overall = retrieve_context(rag_query_overall, n_results=5)

    # propose_offer_structure_and_get_confirmation now returns the modified high_level_offer_info
    # which includes 'positions_details' (the confirmed structure) and 'project_title'.
    # Let's rename the variable for clarity.
    confirmed_offer_structure_details = propose_offer_structure_and_get_confirmation(
        high_level_offer_info,
        retrieved_contexts_overall,
        high_level_offer_info["client_research_summary"], 
        high_level_offer_info["offer_focused_research_summary"]
    )

    if not confirmed_offer_structure_details or not confirmed_offer_structure_details.get("positions_details"):
        print("Error: Could not obtain valid position details after confirmation step. Exiting.")
        return

    # --- AI-GENERATED PROJECT TITLE ---
    print("\n--- Generating Project Title with AI ---")
    system_prompt = "You are an expert business consultant. Generate a concise, professional project title for a client offer."
    user_prompt = (
        "Given the following offer structure and context, suggest a concise, professional project title for the offer.\n"
        f"Client: {confirmed_offer_structure_details.get('client_name', '')}\n"
        f"Industry: {confirmed_offer_structure_details.get('client_industry', '')}\n"
        f"Key Services: {confirmed_offer_structure_details.get('key_services_description', '')}\n"
        f"Focus Areas: {confirmed_offer_structure_details.get('project_focus_tags_input', '')}\n"
        f"Additional Context: {confirmed_offer_structure_details.get('additional_context', '')}\n"
        f"Language: {confirmed_offer_structure_details.get('language', '')}\n"
        f"Structure: {json.dumps(confirmed_offer_structure_details.get('positions_details', []), ensure_ascii=False)}\n"
        "Respond ONLY with the project title, no extra text."
    )
    ai_title = get_llm_response(system_prompt, user_prompt)
    if not isinstance(ai_title, str) or (isinstance(ai_title, dict) and "error" in ai_title):
        print("AI failed to generate a project title, using fallback.")
        confirmed_offer_structure_details["project_title"] = confirmed_offer_structure_details.get("project_title", "AI Generated Project Title")
    else:
        confirmed_offer_structure_details["project_title"] = ai_title.strip()
    print(f"AI Project Title: {confirmed_offer_structure_details['project_title']}")

    final_system_prompt, final_user_prompt = construct_final_drafting_prompts(
        confirmed_offer_structure_details,
        retrieved_contexts_overall,
        confirmed_offer_structure_details["client_research_summary"], 
        confirmed_offer_structure_details["offer_focused_research_summary"]
    )

    ai_generated_json_output = get_llm_json_response( # Renamed variable for clarity
        system_prompt=final_system_prompt,
        user_prompt=final_user_prompt
    )

    print("\n--- AI Generated Final Offer Content (JSON) ---")
    if "error" in ai_generated_json_output:
        print("Failed to generate valid JSON output for the final offer.")
        print(f"Error Type: {ai_generated_json_output['error']}")
        if "details" in ai_generated_json_output:
             print(f"Details: {ai_generated_json_output['details']}")
        if "raw_output" in ai_generated_json_output:
             print("Raw output from LLM that caused parsing error was:")
             print(ai_generated_json_output["raw_output"])
    else:
        # The output should now be the single JSON object with project_title and positions list
        print(json.dumps(ai_generated_json_output, indent=2, ensure_ascii=False))
        print("--- End of AI Generated Content ---")

        # --- BEXIO INTEGRATION ---
        print("\n--- Bexio Integration ---")
        if not BEXIO_API_TOKEN or BEXIO_API_TOKEN == "YOUR_BEXIO_API_TOKEN_PLACEHOLDER_IN_CONFIG":
            print("BEXIO_API_TOKEN is not configured or is using a placeholder.")
            print("Skipping Bexio quote creation.")
            print("Please set the BEXIO_API_TOKEN in your .env file.")
            print("Also, ensure all BEXIO_..._ID constants in config_data.py are correctly set for your Bexio instance.")
        elif not ai_generated_json_output or "positions" not in ai_generated_json_output or not ai_generated_json_output["positions"]:
            print("Error: AI generated content is missing or does not contain positions. Cannot proceed with Bexio quote creation.")
        else:
            confirm_bexio = input("\nDo you want to attempt to create this quote in Bexio? (yes/no): ").lower()
            if confirm_bexio == 'yes':
                bexio_payload = transform_to_bexio_format(ai_generated_json_output)

                if bexio_payload and "error" not in bexio_payload:
                    print("\nSuccessfully transformed data for Bexio. Attempting to create quote...")
                    bexio_response = create_bexio_quote(bexio_payload)
                    # create_bexio_quote already prints success/failure details
                    if bexio_response and "error" in bexio_response:
                         print(f"Bexio quote creation returned an error: {bexio_response.get('message', 'Unknown error')}")
                elif bexio_payload and "error" in bexio_payload:
                    print(f"\nFailed to transform data for Bexio: {bexio_payload.get('error')}")
                else: # Should not happen if transform_to_bexio_format returns None without an error key, but as a fallback
                    print("\nFailed to transform data for Bexio for an unknown reason.")
            else:
                print("Bexio quote creation skipped by user.")
        print("--- End of Bexio Integration ---")
        # --- END BEXIO INTEGRATION ---

    print("\nSidekicks AI Offer Assistant PoC finished.")

if __name__ == "__main__":
    main()
