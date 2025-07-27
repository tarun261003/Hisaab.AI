from HisabAgent.utils.wallet_api import create_class_if_not_exists, create_object, generate_wallet_link
from firebase_admin import credentials, firestore
import firebase_admin
from pathlib import Path
import uuid
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize Firebase with service key
BASE_DIR = Path(__file__).resolve().parent.parent
SERVICE_KEY = BASE_DIR / 'keys' / 'serviceKey.json'

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(str(SERVICE_KEY))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Configure Gemini API for classification
api_key = os.getenv("GEMINI_SUMMARIZE") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    print('[DEBUG] Firebase and Gemini initialized successfully')
else:
    print('[WARNING] Gemini API key not found - classification will use fallback method')
def store_receipt_data(receipt_data: dict, user_id: str = "anonymous") -> dict:
    """
    Stores receipt data in the specified format into Firestore database.
    
    Expected input format:
    {
        "merchant": "Big Bazaar",
        "items": [
            {"name": "Milk", "category": "groceries", "amount": 60},
            {"name": "Detergent", "category": "household", "amount": 75.5}
        ]
    }
    
    Stored format:
    {
        "receipt_id": "r123",
        "uid": "user_001",
        "timestamp": "2025-07-24T10:45:00",
        "merchant": "Big Bazaar",
        "category_summary": {"groceries": 520.0, "household": 75.5},
        "items": [...]
    }
    """
    try:
        # Generate unique receipt ID
        receipt_id = f"r{str(uuid.uuid4())[:8]}"
        
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        # Calculate category summary from items
        category_summary = {}
        items = receipt_data.get("items", [])
        
        for item in items:
            category = item.get("category", "uncategorized")
            amount = float(item.get("amount", 0))
            category_summary[category] = category_summary.get(category, 0) + amount
        
        # Create the structured data
        structured_data = {
            "receipt_id": receipt_id,
            "uid": user_id,
            "timestamp": timestamp,
            "merchant": receipt_data.get("merchant", "Unknown Store"),
            "category_summary": category_summary,
            "items": items
        }
        
        # Store in Firestore
        doc_ref = db.collection("receipts").document(receipt_id)
        doc_ref.set(structured_data)
        
        # Also store under user's collection for easy querying
        user_receipt_ref = db.collection("users").document(user_id).collection("receipts").document(receipt_id)
        user_receipt_ref.set(structured_data)
        
        return {
            "status": "success",
            "receipt_id": receipt_id,
            "message": "Receipt data stored successfully",
            "data": structured_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to store receipt data: {str(e)}"
        }

def generate_wallet_pass(parsed_receipt_json: dict, user_id: str = "anonymous") -> dict:
    """
    Generates a Google Wallet pass link from parsed receipt JSON and stores classified data.

    Steps:
    1. Classifies receipt items using LLM
    2. Creates the Wallet class if it does not exist
    3. Creates a unique Wallet object for the receipt using `create_object()`
    4. Generates a 'Save to Google Wallet' JWT link
    5. Stores only the classified data in your specified format
    
    Parameters:
        parsed_receipt_json (dict): JSON output from receipt_parser.py with:
            - items (list)
            - summary (dict with receipt metadata)
            - qr_link (str): path/URL to use as QR/barcode
            - link (str): URL to access original or full receipt

        user_id (str): Firebase user ID for document structure (default = 'anonymous')

    Returns:
        dict: {
            "status": "success" or "error",
            "link": str (wallet pass link if available),
            "msg": str (error reason if applicable),
            "classified_data": dict (the classified data that was stored)
        }
    """
    try:
        if not api_key:
            return {
                "status": "error",
                "msg": "Gemini API key not configured"
            }
        
        # Validate input
        if parsed_receipt_json.get("status") != "success":
            return {
                "status": "error",
                "msg": f"Invalid receipt data: {parsed_receipt_json.get('msg', 'Unknown error')}"
            }
        
        items = parsed_receipt_json.get("items", [])
        summary = parsed_receipt_json.get("summary", {})
        
        if not items:
            return {
                "status": "error",
                "msg": "No items found in receipt"
            }
        
        # Classify items using LLM
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        classification_prompt = f"""
        Transform this receipt data into the required format with item classification.
        
        Receipt items: {json.dumps(items, indent=2)}
        Store info: {json.dumps(summary, indent=2)}
        
        Classify each item into one of these categories:
        - groceries: Food items, beverages, cooking ingredients
        - household: Cleaning supplies, toiletries, home maintenance items  
        - electronics: Electronic devices, accessories, batteries
        - clothing: Apparel, shoes, accessories
        - health: Medicine, supplements, health products
        - personal_care: Beauty products, hygiene items
        - miscellaneous: Items that don't fit other categories
        
        Return ONLY this JSON format:
        {{
            "merchant": "store_name_from_summary",
            "items": [
                {{
                    "name": "item_name",
                    "category": "classified_category", 
                    "amount": numeric_value_from_item_value,
                    "quantity": item_quantity,
                    "rate": "item_rate"
                }}
            ]
        }}
        """
        
        response = model.generate_content(classification_prompt)
        
        if not response.text:
            return {
                "status": "error",
                "msg": "Empty response from classification API"
            }
        
        # Clean and parse LLM response
        raw_response = response.text.strip()
        if raw_response.startswith("```json"):
            raw_response = raw_response.removeprefix("```json").strip()
        if raw_response.endswith("```"):
            raw_response = raw_response.removesuffix("```").strip()
        
        try:
            classified_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "msg": f"Failed to parse classification response: {str(e)}"
            }
        
        # Prepare receipt data for wallet creation (original format)
        fallback_url = "https://example.com"
        receipt_data = {
            "items": items,
            "summary": summary,
            "qr_link": parsed_receipt_json.get("qr_link") or fallback_url,
            "link": parsed_receipt_json.get("link") or fallback_url
        }
        
        # Create wallet pass
        create_class_if_not_exists()
        success, object_id = create_object(receipt_data)

        if success:
            wallet_link = generate_wallet_link(object_id)
            
            # Store only the classified data in your specified format
            store_result = store_receipt_data(classified_data, user_id)
            
            if store_result["status"] == "success":
                return {
                    "status": "success",
                    "link": wallet_link,
                    "classified_data": store_result["data"],
                    "receipt_id": store_result["receipt_id"]
                }
            else:
                return {
                    "status": "error",
                    "msg": f"Failed to store classified data: {store_result['message']}"
                }
        else:
            return {
                "status": "error",
                "msg": "Wallet object creation failed"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Exception: {str(e)}"
        }
def save_receipt_to_db(receipt_data: dict, user_id: str = "user_001") -> dict:
    """
    Direct function to save receipt data to database.
    If data comes from receipt parser, use process_receipt_json_and_store instead.
    
    Usage example:
    receipt_data = {
        "merchant": "Big Bazaar",
        "items": [
            {"name": "Milk", "category": "groceries", "amount": 60},
            {"name": "Detergent", "category": "household", "amount": 75.5}
        ]
    }
    
    result = save_receipt_to_db(receipt_data, "user_001")
    """
    return store_receipt_data(receipt_data, user_id)

def get_receipt_by_id(receipt_id: str) -> dict:
    """
    Retrieve a receipt by its ID from the database.
    """
    try:
        doc_ref = db.collection("receipts").document(receipt_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return {
                "status": "success",
                "data": doc.to_dict()
            }
        else:
            return {
                "status": "error",
                "message": "Receipt not found"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve receipt: {str(e)}"
        }

def get_user_receipts(user_id: str, limit: int = 50) -> dict:
    """
    Get all receipts for a specific user.
    """
    try:
        receipts_ref = db.collection("users").document(user_id).collection("receipts")
        docs = receipts_ref.limit(limit).stream()
        
        receipts = []
        for doc in docs:
            receipt_data = doc.to_dict()
            receipts.append(receipt_data)
        
        return {
            "status": "success",
            "count": len(receipts),
            "data": receipts
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve user receipts: {str(e)}"
        }
def process_receipt_json_and_store(parsed_receipt_json: dict, user_id: str = "user_001") -> dict:
    """
    Simple method that takes JSON from receipt parser, classifies items with LLM, and stores in database.
    
    Args:
        parsed_receipt_json: JSON output from receipt_parser.py
        user_id: User ID for database storage
    
    Returns:
        dict: Result with receipt_id and stored data
    """
    try:
        if not api_key:
            return {
                "status": "error",
                "message": "Gemini API key not configured"
            }
        
        # Validate input
        if parsed_receipt_json.get("status") != "success":
            return {
                "status": "error",
                "message": f"Invalid receipt data: {parsed_receipt_json.get('msg', 'Unknown error')}"
            }
        
        items = parsed_receipt_json.get("items", [])
        summary = parsed_receipt_json.get("summary", {})
        
        if not items:
            return {
                "status": "error",
                "message": "No items found in receipt"
            }
        
        # Single LLM API call to classify and transform items
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        classification_prompt = f"""
        Transform this receipt data into the required format with item classification.
        
        Receipt items: {json.dumps(items, indent=2)}
        Store info: {json.dumps(summary, indent=2)}
        
        Classify each item into one of these categories:
        - groceries: Food items, beverages, cooking ingredients
        - household: Cleaning supplies, toiletries, home maintenance items  
        - electronics: Electronic devices, accessories, batteries
        - clothing: Apparel, shoes, accessories
        - health: Medicine, supplements, health products
        - personal_care: Beauty products, hygiene items
        - miscellaneous: Items that don't fit other categories
        
        Return ONLY this JSON format:
        {{
            "merchant": "store_name_from_summary",
            "items": [
                {{
                    "name": "item_name",
                    "category": "classified_category", 
                    "amount": numeric_value_from_item_value,
                    "quantity": item_quantity,
                    "rate": "item_rate"
                }}
            ]
        }}
        """
        
        response = model.generate_content(classification_prompt)
        
        if not response.text:
            return {
                "status": "error",
                "message": "Empty response from classification API"
            }
        
        # Clean and parse LLM response
        raw_response = response.text.strip()
        if raw_response.startswith("```json"):
            raw_response = raw_response.removeprefix("```json").strip()
        if raw_response.endswith("```"):
            raw_response = raw_response.removesuffix("```").strip()
        
        try:
            classified_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"Failed to parse classification response: {str(e)}"
            }
        
        # Store in database
        result = store_receipt_data(classified_data, user_id)
        
        # Add summary info to response
        if result["status"] == "success":
            category_summary = {}
            for item in classified_data.get("items", []):
                category = item.get("category", "miscellaneous")
                amount = float(item.get("amount", 0))
                category_summary[category] = category_summary.get(category, 0) + amount
            
            result.update({
                "category_summary": category_summary,
                "total_amount": sum(category_summary.values()),
                "store_name": classified_data.get("merchant", "Unknown Store"),
                "items_count": len(classified_data.get("items", []))
            })
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process receipt: {str(e)}"
        }