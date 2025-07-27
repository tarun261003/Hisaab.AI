# main.py (Revised)

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from data_handler import (
    generate_text_embedding,
    retrieve_relevant_chunks_rag,
    store_receipt_in_firestore, # Use for ingesting raw receipts
    load_and_chunk_text_file,    # For demo general RAG content
    query_structured_receipt_data,
    parse_time_metric # New helper
)
from llm_service import generate_response_from_llm
from google.generativeai import configure # For embedding API key config

# --- Environment Variables Check ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    print("Please set it before running. E.g., export GOOGLE_API_KEY='YOUR_API_KEY'")
    exit(1)
else:
    configure(api_key=GOOGLE_API_KEY)

if not FIREBASE_SERVICE_ACCOUNT_PATH or not os.path.exists(FIREBASE_SERVICE_ACCOUNT_PATH):
    print("Error: FIREBASE_SERVICE_ACCOUNT_PATH environment variable not set or path is invalid.")
    print("Please set it to the path of your Firebase service account key JSON.")
    print("E.g., export FIREBASE_SERVICE_ACCOUNT_PATH='/path/to/your/serviceAccountKey.json'")
    exit(1)

# --- Intent Recognition and Parameter Extraction (using LLM as a Tool) ---
def analyze_query_for_structured_data(user_query: str) -> Optional[Dict]:
    """
    Uses the LLM to analyze the user query for intent to retrieve structured data
    and extract relevant parameters.

    Returns a dictionary of extracted parameters (e.g., {'time_range': 'last two weeks', 'merchant': 'Big Bazaar'})
    or None if no structured query intent is detected.
    """
    prompt = f"""
    Analyze the following user query to determine if it asks for specific transaction details (like purchases from a certain merchant, within a time frame, or specific items/categories).
    If it does, extract the relevant parameters in JSON format.
    Possible parameters to extract:
    - "uid": (mandatory, assume 'user_001' for this demo unless specified)
    - "time_range": (e.g., "last two weeks", "last week", "today", "yesterday", "last month", or "specific date:YYYY-MM-DD")
    - "merchant": (e.g., "Big Bazaar", "Food Mart")
    - "category": (e.g., "groceries", "household", "vegetables", "drinks")
    - "item_name": (e.g., "Milk", "Rice", "Apples")

    If the query is for general knowledge or open-ended questions not about specific transactions, return an empty JSON object {{}}.
    Do not include any other text in your response, only the JSON.

    User Query: "{user_query}"

    JSON Parameters:
    """

    try:
        model = generate_response_from_llm.__globals__['llm_model'] # Access the model directly
        response = model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        print(f"LLM extracted JSON: {json_str}")
        extracted_params = json.loads(json_str)

        # Default UID for demo if not specified
        if "uid" not in extracted_params:
            extracted_params["uid"] = "user_001" # Default to a specific user for this demo

        return extracted_params if any(k for k in extracted_params if k != "uid") else None
    except json.JSONDecodeError as e:
        print(f"LLM did not return valid JSON for parameter extraction: {e}")
        return None
    except Exception as e:
        print(f"Error analyzing query for structured data: {e}")
        return None

# --- RAG Workflow Function ---
def run_rag_system_with_dynamic_query(user_query: str) -> str:
    """
    Executes the RAG workflow, dynamically choosing between structured query
    and semantic search based on user intent.
    """
    print(f"\n--- Running RAG System for Query: '{user_query}' ---")

    extracted_params = analyze_query_for_structured_data(user_query)

    context_for_llm = ""
    retrieved_structured_data = []

    if extracted_params:
        print("Structured query intent detected. Attempting to retrieve structured data...")
        uid = extracted_params.get("uid")
        merchant = extracted_params.get("merchant")
        category = extracted_params.get("category")
        item_name = extracted_params.get("item_name")

        # Parse time range if present
        start_date_param = None
        end_date_param = None
        if "time_range" in extracted_params and extracted_params["time_range"]:
            # Need to pass the original user query to parse_time_metric
            start_date_param, end_date_param = parse_time_metric(user_query)


        retrieved_structured_data = query_structured_receipt_data(
            uid=uid,
            start_date=start_date_param,
            end_date=end_date_param,
            merchant=merchant,
            category=category,
            item_name=item_name,
            limit=10 # Adjust limit as needed
        )

        if retrieved_structured_data:
            print(f"Successfully retrieved {len(retrieved_structured_data)} structured data entries.")
            # Format structured data for LLM context
            context_for_llm = "The following relevant transaction data was found:\n\n"
            for r in retrieved_structured_data:
                context_for_llm += f"Receipt ID: {r.get('receipt_id')}, Merchant: {r.get('merchant')}, Timestamp: {r.get('timestamp')}, Categories: {r.get('category_summary')}, Items: {[item['name'] for item in r.get('items', [])]}\n"
            context_for_llm += "\nBased on this information, "
        else:
            print("No structured data found for the given criteria. Falling back to semantic search.")
    else:
        print("No structured query intent detected. Proceeding with semantic search (RAG).")

    # If no structured data was retrieved or no structured query intent, proceed with RAG (semantic search)
    if not context_for_llm:
        query_embedding = generate_text_embedding(user_query)
        if not query_embedding:
            return "Failed to generate embedding for your query. Please try again."

        relevant_chunks_rag = retrieve_relevant_chunks_rag(query_embedding, limit=3)
        if relevant_chunks_rag:
            print(f"Found {len(relevant_chunks_rag)} relevant RAG chunks.")
            context_for_llm = "\n\n".join([chunk.get("text", "") for chunk in relevant_chunks_rag if chunk.get("text")])
        else:
            print("No relevant RAG chunks found.")


    # 4. Generate response using LLM with context
    llm_response = generate_response_from_llm(user_query, context_for_llm)

    return llm_response

# --- Main Execution ---
if __name__ == "__main__":
    # --- Step 0: Optional: Ingest initial data (if not already done) ---
    print("--- Checking for and Ingesting Sample Data (if needed) ---")
    # Using a dummy query to check if any receipts exist
    check_receipts = query_structured_receipt_data(uid="user_001", limit=1)
    if not check_receipts:
        sample_receipt_data = [
            {
                "receipt_id": "r123_test_main",
                "uid": "user_001",
                "timestamp": "2025-07-24T10:45:00", # Last 2 weeks
                "merchant": "Big Bazaar",
                "category_summary": {"groceries": 520.0, "household": 75.5},
                "items": [
                    {"name": "Milk", "category": "groceries", "amount": 60},
                    {"name": "Detergent", "category": "household", "amount": 75.5},
                    {"name": "Rice", "category": "groceries", "amount": 460}
                ]
            },
            {
                "receipt_id": "r124_test_main",
                "uid": "user_001",
                "timestamp": "2025-07-20T15:30:00", # Last 2 weeks
                "merchant": "Food Mart",
                "category_summary": {"groceries": 300.0, "drinks": 50.0},
                "items": [
                    {"name": "Apples", "category": "groceries", "amount": 100},
                    {"name": "Orange Juice", "category": "drinks", "amount": 50},
                    {"name": "Bread", "category": "groceries", "amount": 200}
                ]
            },
            {
                "receipt_id": "r125_test_main",
                "uid": "user_001",
                "timestamp": "2025-07-10T09:00:00", # More than 2 weeks ago
                "merchant": "Local Store",
                "category_summary": {"vegetables": 150.0},
                "items": [
                    {"name": "Potatoes", "category": "vegetables", "amount": 150}
                ]
            },
            {
                "receipt_id": "r126_test_main",
                "uid": "user_002", # Different user
                "timestamp": "2025-07-23T11:00:00",
                "merchant": "Online Grocer",
                "category_summary": {"groceries": 800.0},
                "items": [
                    {"name": "Pasta", "category": "groceries", "amount": 200},
                    {"name": "Tomato Sauce", "category": "groceries", "amount": 150},
                    {"name": "Cheese", "category": "groceries", "amount": 450}
                ]
            }
        ]
        for receipt in sample_receipt_data:
            store_receipt_in_firestore(receipt)
        print("Ingested sample receipt data.")
    else:
        print("Sample receipt data appears to be in Firestore already. Skipping ingestion.")

    # --- Ingest general RAG data for general questions ---
    general_rag_doc_name = "general_firebase_info"
    # To avoid re-ingesting every time, check if some unique document exists in document_chunks
    try:
        # A quick check for a specific RAG chunk that might indicate general data is there
        dummy_rag_query_embedding = generate_text_embedding("What is Firebase?")
        if not retrieve_relevant_chunks_rag(dummy_rag_query_embedding, limit=1):
            with open("demo_general_rag_doc.txt", "w") as f:
                f.write("""
                Firebase is Google's mobile and web application development platform. It provides a suite of tools that help developers build, deploy, and scale apps quickly. Key Firebase products include Cloud Firestore for flexible NoSQL database, Firebase Authentication for user management, Cloud Functions for serverless backend logic, Firebase Hosting for web content, and Firebase Realtime Database for real-time data synchronization. Firestore offers robust querying and can now support vector search for AI applications. This makes it a powerful backend for Retrieval-Augmented Generation (RAG) systems.
                """)
            general_rag_chunks = load_and_chunk_text_file("demo_general_rag_doc.txt")
            if general_rag_chunks:
                # Store these as general knowledge chunks without a specific receipt ID
                for i, chunk_text in enumerate(general_rag_chunks):
                    rag_embedding = generate_text_embedding(chunk_text)
                    if rag_embedding:
                        doc_ref = data_handler.db.collection(data_handler.FIRESTORE_CHUNKS_COLLECTION).document(f"{general_rag_doc_name}_chunk_{i}")
                        doc_ref.set({
                            "source_doc_name": general_rag_doc_name,
                            "chunk_index": i,
                            "text": chunk_text,
                            "embedding": rag_embedding,
                            "timestamp": firestore.SERVER_TIMESTAMP
                        })
                print(f"Ingested general RAG document '{general_rag_doc_name}'.")
            os.remove("demo_general_rag_doc.txt") # Clean up
        else:
            print("General RAG data appears to be in Firestore already. Skipping ingestion.")
    except Exception as e:
        print(f"Error during general RAG data check/ingestion: {e}")
        print("Ensure Firestore is set up and FIREBASE_SERVICE_ACCOUNT_PATH is correct.")
        exit(1)


    # --- Interactive RAG session ---
    print("\n--- Intelligent RAG System Ready ---")
    print("Type 'exit' to quit.")

    while True:
        user_input = input("\nYour question: ")
        if user_input.lower() == 'exit':
            break

        response = run_rag_system_with_dynamic_query(user_input)
        print(f"\nAI Answer: {response}")