# bexio_utils.py

import requests
import json
import os
from datetime import datetime, timedelta
import re

# Assuming config_data.py will store these constants
from config_data import (
    BEXIO_API_TOKEN, BEXIO_API_URL, BEXIO_USER_ID, BEXIO_CONTACT_ID, BEXIO_CURRENCY_ID,
    BEXIO_LANGUAGE_ID, BEXIO_MWST_TYPE, BEXIO_MWST_IS_NET, BEXIO_UNIT_ID_HOURS,
    BEXIO_ACCOUNT_ID_SERVICES, BEXIO_TAX_ID_STANDARD, BEXIO_BANK_ACCOUNT_ID,
    BEXIO_PAYMENT_TYPE_ID, BEXIO_LOGOPAPER_ID, BEXIO_TEMPLATE_SLUG,
    BEXIO_DOCUMENT_NR, BEXIO_SHOW_POSITION_TAXES
)



def transform_to_bexio_format(llm_offer_json):
    """
    Transforms the AI-generated offer JSON (which includes project title and positions)
    into the JSON format required by the Bexio "Create quote" API.

    Args:
        llm_offer_json (dict): The direct JSON output from the LLM, structured as:
            {
                "project_title": "string",
                "positions": [
                    {
                        "position_id": integer,
                        "type": "Offer Position" | "Text Position",
                        "position_title": "string",
                        "description": "string",
                        // Fields below only for "Offer Position"
                        "estimated_hours_input": number,
                        "hourly_rate_chf": number,
                        "service_area_used": "string",
                        "calculated_price_chf": number
                    },
                    ...
                ]
            }

    Returns:
        dict: The payload ready for the Bexio API, or None if essential data is missing.
    """
    print("\n--- Transforming data for Bexio API ---")

    if not isinstance(llm_offer_json, dict) or \
       "project_title" not in llm_offer_json or \
       "positions" not in llm_offer_json or \
       not isinstance(llm_offer_json["positions"], list):
        print("Error: Input llm_offer_json is not structured as expected (missing 'project_title' or 'positions' list).")
        return None

    project_title = llm_offer_json.get("project_title", "Offer") # Default title if missing
    llm_positions = llm_offer_json.get("positions", [])

    bexio_api_positions = []
    for llm_pos in llm_positions:
        if not isinstance(llm_pos, dict):
            print(f"Warning: Skipping invalid position item (not a dict): {llm_pos}")
            continue

        pos_type = llm_pos.get("type")
        if pos_type == "Offer Position":
            # Extract details for Bexio Offer Position
            total_position_price = llm_pos.get("calculated_price_chf")
            position_title = llm_pos.get("position_title", "Position")
            description = llm_pos.get("description", "")
            position_text = format_bexio_position(position_title, description)
            if total_position_price is None:
                print(f"Warning: Skipping Offer Position '{position_title}' due to missing 'calculated_price_chf'.")
                continue

            bexio_item = {
                "type": "KbPositionCustom",
                "amount": "1",
                "unit_id": BEXIO_UNIT_ID_HOURS,
                "account_id": BEXIO_ACCOUNT_ID_SERVICES,
                "tax_id": BEXIO_TAX_ID_STANDARD,
                "text": position_text,
                "unit_price": str(total_position_price),
                "discount_in_percent": None,
            }
            bexio_api_positions.append(bexio_item)
        elif pos_type == "Text Position":
            position_title = llm_pos.get("position_title", "Text Section")
            description = llm_pos.get("description", "")
            position_text = format_bexio_position(position_title, description)
            bexio_item = {
                "type": "KbPositionText",
                "text": position_text,
                "show_pos_nr": False
            }
            bexio_api_positions.append(bexio_item)
        else:
            print(f"Warning: Skipping position with unknown type: {pos_type} - Title: {llm_pos.get('position_title')}")

    if not bexio_api_positions:
        print("Warning: No 'Offer Position' items found to include in the Bexio quote.")
        # Depending on requirements, you might want to return None or an empty payload,
        # or a payload with no positions if Bexio allows that.
        # For now, let's proceed to create a quote that might be empty if no offer positions were found.

    current_date = datetime.now().strftime("%Y-%m-%d")
    valid_until_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") # Default 30 days validity

    payload = {
        "title": project_title,
        "contact_id": BEXIO_CONTACT_ID, 
        "user_id": BEXIO_USER_ID, 
        # "logopaper_id": BEXIO_LOGOPAPER_ID, # Often specific to Bexio setup, can be optional
        "language_id": BEXIO_LANGUAGE_ID, # e.g., 1 for German, 2 for English
        "bank_account_id": BEXIO_BANK_ACCOUNT_ID, # Default bank account
        "currency_id": BEXIO_CURRENCY_ID, # e.g., 1 for CHF
        "payment_type_id": BEXIO_PAYMENT_TYPE_ID, # Payment terms
        "header": None, # No header text
        "footer": None, # No footer text
        "mwst_type": BEXIO_MWST_TYPE,
        "mwst_is_net": BEXIO_MWST_IS_NET,
        "show_position_taxes": BEXIO_SHOW_POSITION_TAXES,
        "is_valid_from": current_date,
        "is_valid_until": valid_until_date,
        "positions": bexio_api_positions,
    }

    if BEXIO_DOCUMENT_NR:
        payload["document_nr"] = BEXIO_DOCUMENT_NR
    if BEXIO_LOGOPAPER_ID: # Note: Ensure BEXIO_LOGOPAPER_ID can be None or a valid integer
         payload["logopaper_id"] = BEXIO_LOGOPAPER_ID
    if BEXIO_TEMPLATE_SLUG:
        payload["template_slug"] = BEXIO_TEMPLATE_SLUG

    print(f"Bexio payload generated: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    return payload

def format_bexio_position(title, description):
    """
    Formats a position for Bexio with bold title and bullet points as HTML.
    - Title is wrapped in <strong>...</strong> and followed by <br />
    - Bullet points (lines starting with -, *, or •) are wrapped in <ul><li>...</li></ul>
    - Other lines are joined with <br />
    - All ß are replaced with ss (Swiss standard)
    """
    import re
    title = title.replace("ß", "ss")
    description = description.replace("ß", "ss")
    lines = description.splitlines()
    bullets = []
    normal_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[-*•]\s+', stripped):
            bullets.append(stripped.lstrip('-*•').strip())
        elif stripped:
            normal_lines.append(stripped)
    html = f"<strong>{title}</strong>"
    if normal_lines:
        html += "<br />" + "<br />".join(normal_lines)
    if bullets:
        html += "<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"
    return html

def create_bexio_quote(bexio_payload):
    """
    Sends the prepared payload to the Bexio API to create a new quote.

    Args:
        bexio_payload (dict): The JSON payload for the Bexio API.

    Returns:
        dict: The JSON response from the Bexio API or an error dictionary.
    """
    print("\n--- Sending data to Bexio API ---")
    if not BEXIO_API_TOKEN or BEXIO_API_TOKEN == "YOUR_BEXIO_API_TOKEN_PLACEHOLDER_IN_CONFIG":
        print("Error: BEXIO_API_TOKEN is not configured or is a placeholder. Cannot send request.")
        print("Please set BEXIO_API_TOKEN in your .env file.")
        return {"error": "BEXIO_API_TOKEN not configured"}

    headers = {
        'Accept': "application/json",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {BEXIO_API_TOKEN}",
    }

    try:
        response = requests.post(BEXIO_API_URL, data=json.dumps(bexio_payload), headers=headers, timeout=30)
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        print(f"Bexio API Response Status: {response.status_code}")
        response_json = response.json()
        print("Bexio API Response Content:")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        return response_json
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
        return {"error": "HTTPError", "status_code": response.status_code, "message": response.text}
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception occurred: {req_err}")
        return {"error": "RequestException", "message": str(req_err)}
    except json.JSONDecodeError as json_err:
        print(f"Failed to decode JSON response: {json_err}")
        print(f"Raw response content: {response.text}")
        return {"error": "JSONDecodeError", "message": str(json_err), "raw_response": response.text}

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    print("Testing bexio_utils.py...")

    # Mockup of ai_positions_json (output from LLM)
    mock_ai_positions = [
        {
            "position_id": "P1",
            "position_title": "Initial Project Setup and Consultation",
            "description": "This phase includes the initial project setup, requirements gathering, and detailed consultation to align on project goals and deliverables. We will define the project scope and create a roadmap.",
            "service_tags": ["consultation", "project setup", "requirements gathering"]
        },
        {
            "position_id": "P2",
            "position_title": "Development Phase 1: Core Features",
            "description": "Development of the core features as identified in the consultation phase. This includes backend logic, API development, and basic UI/UX implementation. Regular updates and feedback sessions will be held.",
            "service_tags": ["development", "backend", "frontend", "core features"]
        }
    ]

    # Mockup of offer_details (as constructed in offer_workflow.py)
    mock_offer_details = {
        "project_title": "Custom Software Development for Client X",
        "client_name": "Client X",
        "client_industry": "Technology",
        "key_services_description": "End-to-end software development.",
        "project_focus_tags_input": "software, development, agile",
        "estimated_num_components": "2",
        "positions_details": [
            {
                "title_input": "Initial Project Setup and Consultation",
                "description_input": "Key points for setup and consultation",
                "service_area_input": "Strategy & Concept",
                "hours_input": 20.0,
                "calculated_price_info": {
                    "calculated_price_chf": 3600.0,
                    "hourly_rate_chf": 180.0,
                    "service_area_used": "Strategy & Concept",
                    "estimated_hours_input": 20.0
                }
            },
            {
                "title_input": "Development Phase 1: Core Features",
                "description_input": "Key points for dev phase 1",
                "service_area_input": "MVP Development",
                "hours_input": 80.0,
                "calculated_price_info": {
                    "calculated_price_chf": 12800.0,
                    "hourly_rate_chf": 160.0,
                    "service_area_used": "MVP Development",
                    "estimated_hours_input": 80.0
                }
            }
        ]
    }

    print("\n--- Test: transform_to_bexio_format ---")
    bexio_payload_test = transform_to_bexio_format(mock_ai_positions)

    if bexio_payload_test and "error" not in bexio_payload_test:
        print("\nSuccessfully transformed data for Bexio.")
        # print(json.dumps(bexio_payload_test, indent=2, ensure_ascii=False)) # Already printed inside

        # To test sending, uncomment the following lines and ensure BEXIO_API_TOKEN is set
        # print("\n--- Test: create_bexio_quote (will attempt to send to API) ---")
        # print("Ensure BEXIO_API_TOKEN is set as an environment variable for this test.")
        # if BEXIO_API_TOKEN and BEXIO_API_TOKEN != "YOUR_BEXIO_API_TOKEN":
        #     response = create_bexio_quote(bexio_payload_test)
        #     print("\nResponse from create_bexio_quote:")
        #     print(json.dumps(response, indent=2, ensure_ascii=False))
        # else:
        #     print("\nSkipping create_bexio_quote test as BEXIO_API_TOKEN is not set or is placeholder.")
    else:
        print("\nFailed to transform data for Bexio or error in payload.")

    print("\n--- End of bexio_utils.py tests ---")
