# llm_service.py (Same as before, no changes needed for this specific update)

import os
from typing import List, Dict
from google.generativeai import GenerativeModel, configure, types

# --- LLM Initialization ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Please set it.")

configure(api_key=GOOGLE_API_KEY)

LLM_MODEL_NAME = "gemini-pro"
llm_model = GenerativeModel(model_name=LLM_MODEL_NAME)

# --- LLM Generation Function ---
def generate_response_from_llm(user_query: str, context: str) -> str:
    """
    Generates a response using the LLM, grounded by provided context (text).
    The context can be RAG chunks or a summary of structured data.
    """
    if not context.strip():
        print("Warning: No context provided to LLM. Response might be less accurate.")
        # Fallback to direct query if no context
        prompt = f"User Question: {user_query}"
        try:
            response = llm_model.generate_content(prompt)
            return response.text
        except types.BlockedPromptException as e:
            print(f"Prompt was blocked by safety settings: {e}")
            return "I'm sorry, I cannot answer that question due to safety concerns."
        except Exception as e:
            print(f"Error calling LLM without context: {e}")
            return "I am unable to generate a response at this time."


    # Construct the augmented prompt for RAG
    prompt = f"""
    You are an AI assistant. Answer the user's question based on the provided information.
    If the information is not in the context, clearly state "I don't have enough information to answer that question based on the provided context."
    Do not make up information.

    Context:
    {context}

    User Question: {user_query}

    Answer:
    """

    print("\n--- Sending to LLM with Augmented Prompt ---")
    try:
        response = llm_model.generate_content(prompt)
        return response.text
    except types.BlockedPromptException as e:
        print(f"Prompt was blocked by safety settings: {e}")
        return "I'm sorry, I cannot answer that question due to safety concerns."
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return "I am unable to generate a response at this time."

# (The `if __name__ == "__main__":` block can remain for testing `llm_service` independently)