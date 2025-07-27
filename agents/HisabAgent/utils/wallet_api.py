import json, requests, jwt, datetime
from google.auth.transport.requests import Request
from google.oauth2 import service_account
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
SERVICE_ACCOUNT_FILE = WALLET_KEY  # Path to your service account key file
SCOPES = ['https://www.googleapis.com/auth/wallet_object.issuer']
ISSUER_ID = "3388000000022958962"
CLASS_ID = f"{ISSUER_ID}.dynamic_receipt_class"
CLASS_URL = "https://walletobjects.googleapis.com/walletobjects/v1/genericClass"
OBJECT_URL = "https://walletobjects.googleapis.com/walletobjects/v1/genericObject"

# === AUTH ===
def get_access_token():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        if "Invalid JWT Signature" in str(e):
            print("❌ Service account credentials are invalid or corrupted")
            print("💡 Please regenerate your service account key from Google Cloud Console")
            print("🔗 https://console.cloud.google.com/iam-admin/serviceaccounts")
        else:
            print(f"❌ Authentication error: {str(e)}")
        raise e

def get_headers():
    try:
        token = get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        print(f"❌ Failed to get authentication headers: {str(e)}")
        raise e

# === UTIL: Auto create class if needed ===
def create_class_if_not_exists():
    try:
        response = requests.get(f"{CLASS_URL}/{CLASS_ID}", headers=get_headers())
        if response.status_code == 404:
            class_payload = {
                "id": CLASS_ID,
                "issuerName": "Hisab.AI",
                "reviewStatus": "UNDER_REVIEW",
                "header": {
                    "defaultValue": {"language": "en-US", "value": "Receipt"}
                },
                "cardTitle": {
                    "defaultValue": {"language": "en-US", "value": "Retail Receipt"}
                }
            }
            create_response = requests.post(CLASS_URL, headers=get_headers(), json=class_payload)
            if create_response.status_code not in [200, 201]:
                print(f"Class creation failed: {create_response.status_code} {create_response.text}")
                return False
        return True
    except Exception as e:
        print(f"Error creating class: {str(e)}")
        return False

# === CREATE OBJECT ===
def create_object(receipt_data):
    create_class_if_not_exists()

    # Ensure minimal structure
    summary = receipt_data.get("summary", {})
    items = receipt_data.get("items", [])
    store = summary.get("store_name", "Unknown Store")
    date = summary.get("date", "DD-MM-YYYY")
    total = summary.get("total_paid", "0.00")

    # Dynamically hash a unique object ID
    unique_str = f"{store}_{date}_{total}"
    hashed_id = hashlib.md5(unique_str.encode()).hexdigest()
    object_id = f"{ISSUER_ID}.{hashed_id[:15]}"

    # Create item summary (max 5)
    item_summary = "\n".join(
        f"{item.get('name')} x{item.get('quantity')} @ ₹{item.get('rate')} = ₹{item.get('value')}"
        for item in items[:5]
    ) or "No item data available"

    qr_value = receipt_data.get("qr_link") or receipt_data.get("link") or "https://example.com"
    uri_link = receipt_data.get("link") or "https://example.com"

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

    try:
        response = requests.post(OBJECT_URL, headers=get_headers(), json=object_payload)
        if response.status_code in [200, 201, 409]:
            return True, object_id
        else:
            print(f"Object creation failed: {response.status_code} {response.text}")
            return False, object_id
    except Exception as e:
        print(f"Error creating object: {str(e)}")
        return False, object_id

# === GENERATE WALLET LINK ===
def generate_wallet_link(object_id):
    try:
        # Check if cryptography is available
        try:
            import cryptography
        except ImportError:
            print("❌ Missing dependency: cryptography")
            print("Please install it with: pip install cryptography")
            return None
            
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            service_account_info = json.load(f)

        jwt_payload = {
            "iss": service_account_info['client_email'],
            "aud": "google",
            "typ": "savetowallet",
            "iat": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
            "payload": {"genericObjects": [{"id": object_id}]}
        }

        signed_jwt = jwt.encode(jwt_payload, service_account_info['private_key'], algorithm="RS256")
        return f"https://pay.google.com/gp/v/save/{signed_jwt}"
        
    except Exception as e:
        print(f"Error generating wallet link: {str(e)}")
        if "Algorithm 'RS256' could not be found" in str(e):
            print("💡 Solution: Install cryptography with: pip install cryptography")
        return None

# === COMPLETE WALLET FLOW ===
def create_wallet_pass(receipt_data):
    """
    Complete flow: Create wallet object and generate JWT link
    Returns: (success: bool, wallet_link: str or None, object_id: str)
    """
    try:
        # Create class if needed
        if not create_class_if_not_exists():
            return False, None, None
            
        # Create object
        success, object_id = create_object(receipt_data)
        if not success:
            return False, None, object_id
            
        # Generate wallet link
        wallet_link = generate_wallet_link(object_id)
        if not wallet_link:
            return False, None, object_id
            
        return True, wallet_link, object_id
        
    except Exception as e:
        if "Invalid JWT Signature" in str(e) or "RefreshError" in str(e):
            print("🔄 Authentication failed, trying fallback approach...")
            try:
                from .wallet_api_fallback import create_wallet_pass_fallback
                return create_wallet_pass_fallback(receipt_data)
            except ImportError:
                print("❌ Fallback module not available")
                return False, None, None
        else:
            print(f"Error in complete wallet flow: {str(e)}")
            return False, None, None

# === MAIN FUNCTION WITH AUTO-FALLBACK ===
def create_wallet_pass_safe(receipt_data):
    """
    Safe wallet pass creation with automatic fallback
    This is the recommended function to use
    """
    try:
        # Try main approach first
        success, wallet_link, object_id = create_wallet_pass(receipt_data)
        if success:
            return True, wallet_link, object_id
        else:
            # Try fallback approach
            print("🔄 Main approach failed, using fallback...")
            from .wallet_api_fallback import create_wallet_pass_fallback
            return create_wallet_pass_fallback(receipt_data)
            
    except Exception as e:
        if "Invalid JWT Signature" in str(e) or "RefreshError" in str(e):
            print("🔄 Using JWT-only fallback due to authentication issues...")
            try:
                from .wallet_api_fallback import create_wallet_pass_fallback
                return create_wallet_pass_fallback(receipt_data)
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {str(fallback_error)}")
                return False, None, None
        else:
            print(f"❌ Wallet creation error: {str(e)}")
            return False, None, None