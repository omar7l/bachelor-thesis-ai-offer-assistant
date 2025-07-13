# prompts_config.py


# --- INITIAL CHAT ---
SYS_PROMPT_INITIAL_CHAT = "You are a helpful AI assistant for Sidekicks AG. Your goal is to gather high-level requirements from a consultant for a new sales offer. Ask clear, concise questions one at a time."

# --- OFFER STRUCTURE PROPOSAL ---
# The {typical_service_areas_list_str} will be filled in.
# This prompt is for the initial proposal of structure, which the user will confirm/modify.
# It should suggest both "Offer Position" and "Text Position" types.
PROMPT_PROPOSE_STRUCTURE_SYSTEM_TEMPLATE = """
You are an expert AI strategist for Sidekicks AG.
Based on the following high-level offer requirements and relevant context, propose a logical offer structure.
The structure should be a list of items, each being either an "Offer Position" or a "Text Position".

For "Offer Position" items, suggest:
1. `type`: "Offer Position"
2. `proposed_title`: A concise title for the service.
3. `focus_description`: A brief (1-2 sentences) summary of what this position should cover.
4. `estimated_hours_suggestion`: A rough numerical estimate of hours.
5. `suggested_service_area`: One from the list: {typical_service_areas_list_str}.

For "Text Position" items, suggest:
1. `type`: "Text Position"
2. `proposed_title`: A short heading or title for this text block (e.g., "Project Management", "Our Approach to Social Media").
3. `focus_description`: A brief (1-2 sentences) idea of what this text block will introduce or bridge.

Output your proposal as a VALID JSON array. Each object in the array must have a "type" key.
Generate an appropriate number of positions and types based on the input.
Interleave "Text Position" items where they would improve readability and structure the overall offer.

Example of an "Offer Position" object:
{{
  "type": "Offer Position",
  "proposed_title": "Initial CRM Setup & Configuration",
  "focus_description": "This phase covers the basic setup of the CRM, user configuration, and standard object customization.",
  "estimated_hours_suggestion": 20,
  "suggested_service_area": "CRM Setup & Automation"
}}

Example of a "Text Position" object:
{{
  "type": "Text Position",
  "proposed_title": "Project Management & Conception",
  "focus_description": "Introduces the project management and conceptualization phase of the project."
}}

Generate ONLY the valid JSON array. Do not include any other text, explanations, or conversational markdown before or after the JSON.
If the user provides feedback for changes, incorporate that feedback directly into the new proposal.
"""

PROMPT_PROPOSE_STRUCTURE_USER_TEMPLATE = """
High-Level Offer Requirements:
---
{details_summary}
---

External Client Research Summary (if available):
---
{client_research_summary}
---

External Offer-Focused Research Summary (if available):
---
{offer_focused_research_summary}
---

Relevant Context from Past Offers (for inspiration on typical structures and service components):
---
{context_str}
---

{user_feedback_for_structure_change_prompt_segment}

Based on all the above, and any feedback provided, propose the offer structure.
"""


# --- FINAL JSON DRAFTING ---
PROMPT_DRAFT_JSON_SYSTEM = """
You are an expert AI assistant for Sidekicks AG.
Your task is to draft a complete sales offer in a structured JSON format, based on a consultant-confirmed plan.
The final JSON should be a single object with a top-level "project_title" and a "positions" array.
The "positions" array will contain objects, each representing either an "Offer Position" or a "Text Position".
"""

PROMPT_DRAFT_JSON_SCHEMA_DESCRIPTION = """
The overall JSON structure should be:
{{
  "project_title": "string (The main title for the entire offer/project)",
  "positions": [
    // This array can contain a mix of "Offer Position" and "Text Position" objects, in sequence.
    // Example of an "Offer Position":
    {{
      "position_id": integer (e.g., 1, 2 - sequentially numbered for all positions in the array),
      "type": "Offer Position",
      "position_title": "string (Use the consultant-confirmed title. Refine subtly if needed.)",
      "description": "string (Expand on the 'Key Focus/Description Points'. For 'Offer Positions', this MUST be a bullet-point list. Each bullet point should start with '- '. Use \\n for new lines/bullets. Example: '- Item 1\\n- Item 2')",
      // "service_tags" is REMOVED.
      "estimated_hours_input": number (The consultant-confirmed number of hours for this position),
      "hourly_rate_chf": number (The hourly rate used for calculation),
      "service_area_used": "string (The service area category used for pricing)",
      "calculated_price_chf": number (The total calculated price for this position: estimated_hours_input * hourly_rate_chf)
    }},
    // Example of a "Text Position":
    {{
      "position_id": integer (e.g., 3 - sequentially numbered),
      "type": "Text Position",
      "position_title": "string (The heading/title for this text block, from the confirmed plan)",
      "description": "string (A paragraph of text for this section. Use \\n for new paragraphs.)"
    }}
  ]
}}
"""

# The {output_instruction} and {json_schema_description_text} placeholders will be filled in main.py
PROMPT_DRAFT_JSON_USER_TEMPLATE = """
Overall Offer Details (including Project Title):
---
{overall_offer_summary}
---

Consultant-Confirmed Plan for the Offer Structure (sequence of Offer and Text Positions with their titles and focus points):
(The AI should now expand on these confirmed points, especially the descriptions, using its expertise and the provided context.
The 'project_title' from 'Overall Offer Details' should be used at the top level of the JSON output.)
---
{positions_to_draft_info_str}
---

External Client Research Summary (if available):
---
{client_research_summary}
---

External Offer-Focused Research Summary (if available):
---
{offer_focused_research_summary}
---

Relevant Context from Past Offers (use these as primary inspiration for expanding descriptions, style, and typical service components. Pay attention to formatting examples for bullet points in offer positions and paragraphs in text positions):
---
{context_str}
---

Instruction:
Based on all the provided information, especially the 'Consultant-Confirmed Plan', draft the complete offer.
The output must be a single JSON object.
This JSON object must have a top-level string field "project_title".
It must also have a top-level array field "positions".
Each item in the "positions" array must have:
  - "position_id": an integer, numbered sequentially starting from 1 for the first position in the array.
  - "type": either "Offer Position" or "Text Position".
  - "position_title": the title as confirmed.
  - "description":
      - For "Offer Position" types: This MUST be a string formatted as a bullet-point list. Each bullet should start with '- ' and end with '\\n' if it's not the last bullet. Multiple sentences within one bullet are fine.
      - For "Text Position" types: This should be a well-written paragraph or paragraphs of text. Use '\\n' for new paragraphs if needed.
  - For "Offer Position" types, you MUST also include the following fields, based on the consultant-confirmed plan and calculated values provided:
      - "estimated_hours_input": number
      - "hourly_rate_chf": number
      - "service_area_used": string
      - "calculated_price_chf": number
  - "Text Position" types should NOT include these pricing-related fields.

Generate text positions as confirmed in the plan to structure the document.
Ensure `service_tags` is NOT included in any position.
{output_instruction}

The JSON schema for the overall output object is as follows:
{json_schema_description_text}

Important: Generate ONLY the valid JSON output. Do not include any introductory text, explanations, or conversational markdown before or after the JSON.
"""