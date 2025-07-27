# data_handler.py (Revised)

import os
import json
from typing import List, Dict, Tuple, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.generativeai.types import EmbeddingsResponse
from google.generativeai import generate_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from datetime import datetime, timedelta

# --- Firebase Initialization ---
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

if FIREBASE_CREDENTIALS_PATH and os.path.exists(FIREBASE_CREDENTIALS_PATH):
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
else:
    db = None
    print("WARNING: Firebase service account path not found or invalid.")
    print("Please set FIREBASE_SERVICE_ACCOUNT_PATH environment variable.")

# --- Constants ---
FIRESTORE_CHUNKS_COLLECTION = "document_chunks" # For RAG vector search
FIRESTORE_RECEIPTS_COLLECTION = "user_receipts" # For structured queries
EMBEDDING_MODEL_NAME = "text-embedding-004"

# --- Data Loading and Chunking (for RAG) ---
# (Keep load_and_chunk_pdf/text_file as is from previous version if needed,
# or adapt to process structured receipt data for RAG context.)

# For the RAG chunks, we'll create a summary or string representation of the receipt
def create_rag_chunk_from_receipt(receipt: Dict) -> str:
    """Creates a text chunk suitable for RAG from a receipt dictionary."""
    summary = f"Receipt ID: {receipt.get('receipt_id', 'N/A')}\n"
    summary += f"User ID: {receipt.get('uid', 'N/A')}\n"
    summary += f"Timestamp: {receipt.get('timestamp', 'N/A')}\n"
    summary += f"Merchant: {receipt.get('merchant', 'N/A')}\n"
    summary += "Categories: " + ", ".join([f"{k}: {v}" for k, v in receipt.get('category_summary', {}).items()]) + "\n"
    summary += "Items: " + ", ".join([f"{item.get('name')} ({item.get('amount')})" for item in receipt.get('items', [])])
    return summary

# --- Embedding Generation (same as before) ---
def generate_text_embedding(text: str) -> List[float]:
    """Generates an embedding for a given text using the specified model."""
    try:
        response: EmbeddingsResponse = generate_embeddings(model=EMBEDDING_MODEL_NAME, content=text)
        if response and hasattr(response, 'embedding') and hasattr(response.embedding, 'values'):
            return response.embedding.values
        else:
            print(f"Warning: No embedding values found for text. Response: {response}")
            return []
    except Exception as e:
        print(f"Error generating embedding for text: {e}")
        return []

# --- Firestore Operations ---
def store_receipt_in_firestore(receipt_data: Dict):
    """Stores a full receipt document in the user_receipts collection."""
    if db is None:
        print("Firestore not initialized. Cannot store receipt.")
        return

    receipt_id = receipt_data.get("receipt_id")
    if not receipt_id:
        print("Error: Receipt ID is required to store the receipt.")
        return

    try:
        doc_ref = db.collection(FIRESTORE_RECEIPTS_COLLECTION).document(receipt_id)
        doc_ref.set(receipt_data)
        print(f"Receipt '{receipt_id}' stored in '{FIRESTORE_RECEIPTS_COLLECTION}'.")

        # Also store a RAG chunk for semantic search on the receipt content
        rag_chunk_text = create_rag_chunk_from_receipt(receipt_data)
        rag_embedding = generate_text_embedding(rag_chunk_text)
        if rag_embedding:
            chunk_doc_ref = db.collection(FIRESTORE_CHUNKS_COLLECTION).document(f"receipt_rag_{receipt_id}")
            chunk_doc_ref.set({
                "source_receipt_id": receipt_id,
                "text": rag_chunk_text,
                "embedding": rag_embedding,
                "timestamp": firestore.SERVER_TIMESTAMP # Use server timestamp for consistency
            })
            print(f"RAG chunk for receipt '{receipt_id}' stored in '{FIRESTORE_CHUNKS_COLLECTION}'.")

    except Exception as e:
        print(f"Error storing receipt '{receipt_id}': {e}")


def retrieve_relevant_chunks_rag(query_embedding: List[float], limit: int = 5) -> List[Dict]:
    """
    Performs a vector similarity search in Firestore (on document_chunks collection).
    This is the semantic search part.
    (Still uses the local simulation due to SDK limitation, as discussed previously)
    """
    if db is None:
        print("Firestore not initialized. Cannot retrieve chunks.")
        return []

    print(f"Searching Firestore for top {limit} relevant RAG chunks...")
    try:
        collection_ref = db.collection(FIRESTORE_CHUNKS_COLLECTION)
        docs = collection_ref.stream()
        all_chunks = []
        for doc in docs:
            doc_data = doc.to_dict()
            if 'embedding' in doc_data and doc_data['embedding']:
                all_chunks.append({
                    "text": doc_data.get('text'),
                    "embedding": doc_data['embedding'],
                    "source_receipt_id": doc_data.get('source_receipt_id'),
                    "timestamp": doc_data.get('timestamp')
                })

        # --- Local Cosine Similarity (Inefficient Demo Workaround) ---
        def cosine_similarity(vec1, vec2):
            from numpy.linalg import norm
            from numpy import dot
            if not vec1 or not vec2: return -1
            vec1 = [float(x) for x in vec1]
            vec2 = [float(x) for x in vec2]
            if not any(vec1) or not any(vec2): return 0.0
            return dot(vec1, vec2) / (norm(vec1) * norm(vec2))

        scored_chunks = []
        for chunk in all_chunks:
            if chunk['embedding']:
                score = cosine_similarity(query_embedding, chunk['embedding'])
                if score is not None:
                    scored_chunks.append({"score": score, "chunk": chunk})

        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        return [item['chunk'] for item in scored_chunks[:limit]]

    except Exception as e:
        print(f"Error retrieving relevant RAG chunks from Firestore: {e}")
        return []

def query_structured_receipt_data(
    uid: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    merchant: Optional[str] = None,
    category: Optional[str] = None, # For querying items within receipts
    item_name: Optional[str] = None, # For querying specific item names
    limit: int = 10
) -> List[Dict]:
    """
    Dynamically queries structured receipt data from Firestore based on parameters.
    This replaces the RAG's semantic search if a structured query is detected.
    """
    if db is None:
        print("Firestore not initialized. Cannot query structured data.")
        return []

    print(f"Querying structured receipt data for UID: {uid}...")
    receipts_ref = db.collection(FIRESTORE_RECEIPTS_COLLECTION)
    query = receipts_ref.where("uid", "==", uid)

    if start_date:
        query = query.where("timestamp", ">=", start_date.isoformat()) # Timestamps are strings in your data
        print(f"  Filtering by start_date: {start_date}")
    if end_date:
        query = query.where("timestamp", "<=", end_date.isoformat())
        print(f"  Filtering by end_date: {end_date}")
    if merchant:
        query = query.where("merchant", "==", merchant)
        print(f"  Filtering by merchant: {merchant}")
    if category:
        # For category, we might need a more complex query or denormalization
        # Firestore cannot directly query within arrays of objects for a partial match
        # without array-contains on the *exact object*.
        # For querying `items[].category` effectively, consider:
        # 1. Denormalizing: Add a `categories_array` field to the receipt document
        #    containing a list of all categories in the receipt, then use `array_contains`.
        # 2. Collection Group Query: If `items` were a subcollection (not suitable for your JSON).
        # 3. Fetching and Filtering: Fetch all relevant receipts and filter items locally (less efficient).
        # For this demo, let's assume we can filter by the top-level category_summary keys for simplicity
        # or we will filter items locally after fetching.
        query = query.where(f"category_summary.{category}", ">", 0) # Assumes category exists in summary with > 0 amount
        print(f"  Filtering by category_summary: {category}")

    # No direct query for array of objects by sub-field `item.name` in Firestore.
    # We will fetch and filter `items` array locally if `item_name` is provided.

    query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)

    try:
        docs = query.stream()
        results = []
        for doc in docs:
            receipt = doc.to_dict()
            if item_name: # Apply local filter for item_name if present
                if any(item.get("name", "").lower() == item_name.lower() for item in receipt.get("items", [])):
                    results.append(receipt)
            else:
                results.append(receipt)

        print(f"Found {len(results)} structured receipts.")
        return results
    except Exception as e:
        print(f"Error querying structured receipt data: {e}")
        return []

# --- Helper for Time Parsing ---
def parse_time_metric(user_query: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parses common time-based phrases in a query and returns start/end datetimes.
    This is a simplified example; a real-world solution might use a more robust NLP library
    or a dedicated date parsing tool.
    """
    now = datetime.now()
    start_date = None
    end_date = None

    query_lower = user_query.lower()

    if "last two weeks" in query_lower:
        start_date = now - timedelta(weeks=2)
        end_date = now
    elif "last week" in query_lower:
        start_date = now - timedelta(weeks=1)
        end_date = now
    elif "today" in query_lower:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif "yesterday" in query_lower:
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif "last month" in query_lower:
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1) # First day of last month
        end_date = now # Up to current date
    # Add more sophisticated parsing as needed (e.g., "between X and Y", "on specific date")

    print(f"Parsed time metric: Start={start_date}, End={end_date}")
    return start_date, end_date

# Example of how to ingest data (can be run as a script or from main.py)
if __name__ == "__main__":
    from google.generativeai import configure
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("Please set the GOOGLE_API_KEY environment variable.")
        exit(1)
    configure(api_key=GOOGLE_API_KEY)

    print("--- Running Data Ingestion Example for Receipts ---")
    sample_receipt_data = [
        {
            "receipt_id": "r123",
            "uid": "user_001",
            "timestamp": "2025-07-24T10:45:00",
            "merchant": "Big Bazaar",
            "category_summary": {"groceries": 520.0, "household": 75.5},
            "items": [
                {"name": "Milk", "category": "groceries", "amount": 60},
                {"name": "Detergent", "category": "household", "amount": 75.5},
                {"name": "Rice", "category": "groceries", "amount": 460}
            ]
        },
        {
            "receipt_id": "r124",
            "uid": "user_001",
            "timestamp": "2025-07-20T15:30:00",
            "merchant": "Food Mart",
            "category_summary": {"groceries": 300.0, "drinks": 50.0},
            "items": [
                {"name": "Apples", "category": "groceries", "amount": 100},
                {"name": "Orange Juice", "category": "drinks", "amount": 50},
                {"name": "Bread", "category": "groceries", "amount": 200}
            ]
        },
        {
            "receipt_id": "r125",
            "uid": "user_001",
            "timestamp": "2025-07-10T09:00:00", # More than 2 weeks ago
            "merchant": "Local Store",
            "category_summary": {"vegetables": 150.0},
            "items": [
                {"name": "Potatoes", "category": "vegetables", "amount": 150}
            ]
        },
        {
            "receipt_id": "r126",
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

    print("\n--- Running Structured Query Test Example ---")
    # Test "What can I cook with the food I bought from the last two weeks?"
    # Simulate extraction of intent:
    user_id = "user_001" # This would come from user session/authentication
    start_date_q, end_date_q = parse_time_metric("What can I cook with the food I bought from the last two weeks?")
    print(f"\nTesting structured query for user '{user_id}' within {start_date_q} to {end_date_q}")
    recent_receipts = query_structured_receipt_data(
        uid=user_id,
        start_date=start_date_q,
        end_date=end_date_q,
        limit=5
    )
    print("\nRecent Receipts:")
    for receipt in recent_receipts:
        print(f"  - {receipt['merchant']} on {receipt['timestamp']} (Items: {[item['name'] for item in receipt['items']]})")

    # Test "What did I buy from Big Bazaar?"
    print("\nTesting structured query for Big Bazaar")
    big_bazaar_receipts = query_structured_receipt_data(uid=user_id, merchant="Big Bazaar")
    for receipt in big_bazaar_receipts:
        print(f"  - {receipt['merchant']} on {receipt['timestamp']} (Items: {[item['name'] for item in receipt['items']]})")

    # Test "What groceries did I buy?" (requires category_summary index or local filtering)
    print("\nTesting structured query for groceries")
    groceries_receipts = query_structured_receipt_data(uid=user_001, category="groceries")
    for receipt in groceries_receipts:
        print(f"  - {receipt['merchant']} on {receipt['timestamp']} (Items: {[item['name'] for item in receipt['items']]})")

    # Test "Did I buy Milk?"
    print("\nTesting structured query for Milk")
    milk_receipts = query_structured_receipt_data(uid=user_001, item_name="Milk")
    for receipt in milk_receipts:
        print(f"  - {receipt['merchant']} on {receipt['timestamp']} (Items: {[item['name'] for item in receipt['items']]})")