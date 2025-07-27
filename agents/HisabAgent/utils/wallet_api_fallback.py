"""
Fallback Wallet API - JWT-only approach without Google Cloud authentication
This bypasses the "Invalid JWT Signature" error by only using JWT generation
"""
import json
import jwt
import datetime
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WALLET_KEY = BASE_DIR / 'keys' / 'hisabai-edde7-e612e581261d.json'

# Check if wallet key file exists
if not WALLET_KEY.exists():
    # Try alternative path
    WALLET_KEY = Path('./hisabai-edde7-e612e581261d.json')
    if not WALLET_KEY.exists():
        raise FileNotFoundError(f"Wallet service account key not found at {WALLET_KEY}")

# === CONFIG ===
SERVICE_ACCOUNT_FILE = WALLET_KEY
ISSUER_ID = "3388000000022958962"
CLASS_ID = f"{ISSUER_ID}.dynamic_receipt_class"

def generate_object_id(store_name, date, total):
    """Generate unique object ID based on receipt data"""
    unique_str = f"{store_name}_{date}_{total}"
    hashed_id = hashlib.md5(unique_str.encode()).hexdigest()
    return f"{ISSUER_ID}.{hashed_id[:15]}"

def generate_wallet_link_jwt_only(receipt_data):
    """
    Generate JWT wallet link without creating objects via API
    This bypasses the authentication issues
    """
    try:
        # Check if cryptography is available
        try:
            import cryptography
        except ImportError:
            print("❌ Missing dependency: cryptography")
            print("Please install it with: pip install cryptography")
            return None, None
            
        # Load service account info
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            service_account_info = json.load(f)

        # Extract receipt data
        summary = receipt_data.get("summary", {})
        items = receipt_data.get("items", [])
        store = summary.get("store_name", "Unknown Store")
        date = summary.get("date", "DD-MM-YYYY")
        total = summary.get("total_paid", "0.00")
        
        # Generate object ID
        object_id = generate_object_id(store, date, total)
        
        # Create item summary (max 5)
        item_summary = "\n".join(
            f"{item.get('name')} x{item.get('quantity')} @ ₹{item.get('rate')} = ₹{item.get('value')}"
            for item in items[:5]
        ) or "No item data available"

        qr_value = receipt_data.get("qr_link") or receipt_data.get("link") or "https://example.com"
        uri_link = receipt_data.get("link") or "https://example.com"

        # Create the complete object payload for JWT
        object_payload = {
            "id": object_id,
            "classId": CLASS_ID,
            "state": "active",
            "header": {
                "defaultValue": {
                    "language": "en-US",
                    "value": f"{store} Receipt"
                }
            },
            "cardTitle": {
                "defaultValue": {
                    "language": "en-US",
                    "value": f"Total Paid: ₹{total}"
                }
            },
            "titleModulesData": [
                {
                    "header": f"Purchased on {date}",
                    "body": f"Gross: ₹{summary.get('gross_total', 'NA')}, Taxes: ₹{summary.get('taxes', 'NA')}, Savings: ₹{summary.get('savings', 'NA')}"
                }
            ],
            "textModulesData": [
                {
                    "header": "Items (Top 5)",
                    "body": item_summary,
                    "id": "items_summary"
                }
            ],
            "barcode": {
                "type": "qrCode",
                "value": qr_value,
                "alternateText": "Scan to view receipt"
            },
            "linksModuleData": {
                "uris": [
                    {
                        "description": "View Full Receipt",
                        "uri": uri_link
                    }
                ]
            }
        }

        # Create JWT payload with the complete object
        jwt_payload = {
            "iss": service_account_info['client_email'],
            "aud": "google",
            "typ": "savetowallet",
            "iat": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
            "payload": {
                "genericObjects": [object_payload]  # Include full object in JWT
            }
        }

        # Sign JWT with private key
        signed_jwt = jwt.encode(
            jwt_payload, 
            service_account_info['private_key'], 
            algorithm="RS256"
        )
        
        wallet_link = f"https://pay.google.com/gp/v/save/{signed_jwt}"
        return wallet_link, object_id
        
    except Exception as e:
        print(f"Error generating wallet link: {str(e)}")
        if "Algorithm 'RS256' could not be found" in str(e):
            print("💡 Solution: Install cryptography with: pip install cryptography")
        return None, None

def create_wallet_pass_fallback(receipt_data):
    """
    Fallback wallet pass creation using JWT-only approach
    Returns: (success: bool, wallet_link: str or None, object_id: str)
    """
    try:
        wallet_link, object_id = generate_wallet_link_jwt_only(receipt_data)
        if wallet_link and object_id:
            return True, wallet_link, object_id
        else:
            return False, None, None
            
    except Exception as e:
        print(f"Error in fallback wallet flow: {str(e)}")
        return False, None, None

# === MAIN FUNCTION WITH FALLBACK ===
def create_wallet_pass_with_fallback(receipt_data):
    """
    Try main wallet API first, fallback to JWT-only approach if authentication fails
    """
    try:
        # Try main wallet API first
        from .wallet_api import create_wallet_pass
        success, wallet_link, object_id = create_wallet_pass(receipt_data)
        if success:
            return True, wallet_link, object_id
        else:
            print("🔄 Main wallet API failed, trying fallback approach...")
            return create_wallet_pass_fallback(receipt_data)
            
    except Exception as e:
        if "Invalid JWT Signature" in str(e) or "RefreshError" in str(e):
            print("🔄 Authentication failed, using JWT-only fallback...")
            return create_wallet_pass_fallback(receipt_data)
        else:
            print(f"❌ Wallet creation error: {str(e)}")
            return False, None, None

if __name__ == "__main__":
    # Test the fallback approach
    test_receipt = {
        "items": [
            {"name": "Rice", "quantity": 2, "rate": "50.00", "value": "100.00"},
            {"name": "Dal", "quantity": 1, "rate": "80.00", "value": "80.00"}
        ],
        "summary": {
            "gross_total": "180.00",
            "savings": "0.00",
            "taxes": "20.00",
            "total_paid": "200.00",
            "date": "26-07-2025",
            "store_name": "DMart Vijayawada"
        },
        "qr_link": "https://example.com/receipt/123",
        "link": "https://example.com/receipt/123"
    }
    
    success, wallet_link, object_id = create_wallet_pass_fallback(test_receipt)
    if success:
        print(f"✅ Fallback wallet link generated!")
        print(f"🆔 Object ID: {object_id}")
        print(f"🔗 Wallet Link: {wallet_link}")
    else:
        print("❌ Fallback approach also failed")