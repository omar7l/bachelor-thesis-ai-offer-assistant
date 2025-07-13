# llm_utils.py

import os
import json
from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError
import numpy as np
import time

# Import configurations
# import prompts_config as pc # No longer needed here
from config_data import LLM_MODEL_CHAT, LLM_MODEL_JSON_DRAFT # <--- ADD THIS

# --- CONFIGURATION ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please add it.")

# --- INITIALIZE CLIENTS ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# --- LLM HELPER FUNCTIONS ---
def get_llm_response(system_prompt: str, user_prompt: str, model: str = None, temperature: float = 0.7, max_retries: int = 3): # <--- CHANGE HERE
    """Generic function to get a response from an LLM."""
    # If no model is passed, use the default chat model from config_data
    if model is None: 
        model = LLM_MODEL_CHAT 

    print(f"\n--- Calling LLM ({model}) ---")
    print(f"System: {system_prompt[:100]}...")
    print(f"User: {user_prompt[:150]}...")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    for attempt in range(max_retries):
        try:
            completion = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            response_content = completion.choices[0].message.content
            print(f"LLM Response (snippet): {response_content[:100]}...")
            return response_content
        except RateLimitError as e:
            wait_time = (2 ** attempt) + np.random.rand() # Exponential backoff
            print(f"Rate limit hit. Retrying in {wait_time:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
        except APIError as e:
            print(f"OpenAI API Error: {e}. Retrying... (Attempt {attempt+1}/{max_retries})")
            time.sleep(5) # General wait for API errors
        except Exception as e:
            print(f"An unexpected error occurred during LLM call: {e}")
            return {"error": "LLM_CALL_FAILED", "details": str(e)} # Return error dict

    print(f"LLM call failed after {max_retries} retries.")
    return {"error": "LLM_CALL_MAX_RETRIES_EXCEEDED", "details": "Max retries reached."}


def get_llm_json_response(system_prompt: str, user_prompt: str, model: str = None, temperature: float = 0.2, max_retries: int = 3): # <--- CHANGE HERE
    """Gets a response from an LLM and attempts to parse it as JSON, using native JSON mode if supported."""
    # If no model is passed, use the default JSON drafting model from config_data
    if model is None: # <--- ADD THIS
        model = LLM_MODEL_JSON_DRAFT # <--- MODIFIED THIS

    print(f"\n--- Calling LLM for JSON Output ({model}) ---")
    print(f"System: {system_prompt[:100]}...")
    print(f"User: {user_prompt[:150]}...")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    for attempt in range(max_retries):
        try:
            # Check if model supports JSON mode (common in newer OpenAI models)
            # Example: "gpt-3.5-turbo-0125", "gpt-4-turbo", "gpt-4-turbo-preview"
            if "0125" in model or "turbo" in model: # Heuristic, adjust if needed
                completion = openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )
            else: # Fallback for models without explicit JSON mode
                 completion = openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature
                )

            raw_output = completion.choices[0].message.content
            print(f"LLM Raw JSON Output (snippet): {raw_output[:100]}...")
            try:
                parsed_json = json.loads(raw_output)
                return parsed_json
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}. LLM did not return valid JSON.")
                print(f"Raw output was: {raw_output}")
                # Optionally, you could try to clean it or re-prompt here in a more complex system
                # For this PoC, we'll let it retry or return an error.
                if attempt < max_retries - 1:
                    print("Retrying LLM call for JSON...")
                    user_prompt += "\n\nIMPORTANT: Your previous response was not valid JSON. Please ensure your entire output is a single, valid JSON object or array as requested, with no surrounding text or explanations."
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                    time.sleep(2) # Short delay before retrying
                    continue
                return {"error": "JSON_PARSE_FAILED", "details": str(e), "raw_output": raw_output}

        except RateLimitError as e:
            wait_time = (2 ** attempt) + np.random.rand()
            print(f"Rate limit hit. Retrying in {wait_time:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
        except APIError as e:
            print(f"OpenAI API Error: {e}. Retrying... (Attempt {attempt+1}/{max_retries})")
            time.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred during LLM JSON call: {e}")
            return {"error": "LLM_JSON_CALL_FAILED", "details": str(e)}

    print(f"LLM JSON call failed after {max_retries} retries.")
    return {"error": "LLM_JSON_CALL_MAX_RETRIES_EXCEEDED", "details": "Max retries reached."}
