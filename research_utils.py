# research_utils.py
import os
from openai import OpenAI
from config_data import OPENROUTER_API_KEY, PERPLEXITY_MODEL_NAME

def ask_for_external_research() -> bool:
    """Asks the consultant if extensive external research is needed."""
    while True:
        response = input("Do you think extensive external research is needed for this offer? (yes/no): ").strip().lower()
        if response == "yes":
            return True
        elif response == "no":
            return False
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

# Initialize OpenRouter client
openrouter_client = None
if OPENROUTER_API_KEY:
    try:
        openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        print("OpenRouter client initialized successfully for Perplexity.")
    except Exception as e:
        print(f"Error initializing OpenRouter client: {e}")
        openrouter_client = None # Ensure it's None if init fails
else:
    print("Warning: OPENROUTER_API_KEY not found in environment. External research via Perplexity will be skipped.")


def perform_client_research(client_name: str, client_industry: str) -> str:
    """
    Performs client-specific research using Perplexity AI via OpenRouter.
    Returns a string with research results or an error/skipped message.
    """
    print(f"\n--- Performing External Client Research for: {client_name} ({client_industry}) via OpenRouter/Perplexity ---")

    if not openrouter_client:
        print("Skipping client research: OpenRouter client not available (OPENROUTER_API_KEY may be missing or initialization failed).")
        return (
            f"Skipped: External client research for {client_name}. "
            f"Reason: OpenRouter client not available."
        )

    research_query = (
        f"Provide a concise business overview of the company '{client_name}' which operates in the '{client_industry}' industry. "
        f"Focus on their main products/services, target market, key strengths, recent significant news or developments, and potential challenges or opportunities. "
        f"Aim for a summary useful for someone preparing a sales offer for them."
    )

    try:
        # #CommentAndMaybeToIntegrateItFurther: Consider adding a timeout to the request
        completion = openrouter_client.chat.completions.create(
            model=PERPLEXITY_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an AI research assistant. Provide concise and factual information."},
                {"role": "user", "content": research_query}
            ],
            temperature=0.7, # Optional: Adjust for desired creativity/factuality
            # max_tokens=500  # Optional: Limit response length
        )
        response_content = completion.choices[0].message.content
        print("--- Client Research via OpenRouter/Perplexity Successful ---")
        print("\n--- Perplexity API Response (Client Research) ---")
        print(response_content)
        print("--- End of Perplexity API Response ---")
        return response_content
    except Exception as e:
        print(f"Error during OpenRouter (Perplexity) client research for '{client_name}': {e}")
        return f"Error: Could not perform client research for {client_name} via OpenRouter. Details: {str(e)}"

def perform_offer_focused_research(project_description: str, focus_tags: list[str] | str) -> str:
    """
    Performs offer-focused research using Perplexity AI via OpenRouter.
    Returns a string with research results or an error/skipped message.
    """
    if isinstance(focus_tags, list):
        focus_tags_str = ", ".join(focus_tags)
    else:
        focus_tags_str = focus_tags

    print(f"\n--- Performing External Offer-Focused Research for: {project_description} (Focus: {focus_tags_str}) via OpenRouter/Perplexity ---")

    if not openrouter_client:
        print("Skipping offer-focused research: OpenRouter client not available (OPENROUTER_API_KEY may be missing or initialization failed).")
        return (
            f"Skipped: External offer-focused research for {project_description}. "
            f"Reason: OpenRouter client not available."
        )

    research_query = (
        f"For a project involving '{project_description}' with a specific focus on '{focus_tags_str}', "
        f"what are the current key trends, emerging technologies, best practices, common challenges, and typical client expectations or success metrics? "
        f"Provide insights that would be valuable for crafting a compelling sales offer position."
    )

    try:
        # #CommentAndMaybeToIntegrateItFurther: Consider adding a timeout to the request
        completion = openrouter_client.chat.completions.create(
            model=PERPLEXITY_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an AI research assistant. Provide concise and factual information related to technology and business trends for a specific offer."},
                {"role": "user", "content": research_query}
            ],
            temperature=0.7, # Optional
            # max_tokens=500  # Optional
        )
        response_content = completion.choices[0].message.content
        print("--- Offer-Focused Research via OpenRouter/Perplexity Successful ---")
        print("\n--- Perplexity API Response (Offer-Focused Research) ---")
        print(response_content)
        print("--- End of Perplexity API Response ---")
        return response_content
    except Exception as e:
        print(f"Error during OpenRouter (Perplexity) offer-focused research for '{project_description}': {e}")
        return f"Error: Could not perform offer-focused research for {project_description} via OpenRouter. Details: {str(e)}"
