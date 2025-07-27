"""
Agent Tool: OCR Receipt Image ➜ Gemini JSON Extractor
Uses Gemini Vision API and downloads from public bucket
"""
import io
import os
import json
import requests
from typing import Dict
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv()

# Configure Gemini API Key - try multiple environment variable names
api_key = os.getenv("GEMINI_SUMMARIZE") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Gemini API key not found. Set GEMINI_SUMMARIZE, GEMINI_API_KEY, or GOOGLE_API_KEY in your .env file")

genai.configure(api_key=api_key)

def download_image_from_public_bucket(image_url: str, local_path: str = None) -> str:
    """
    Downloads image from public bucket URL
    """
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        
        if not local_path:
            # Generate local filename from URL
            filename = os.path.basename(image_url.split('?')[0]) or "receipt_image.jpg"
            local_path = BASE_DIR / "temp_images" / filename
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return str(local_path)
    except Exception as e:
        raise Exception(f"Failed to download image: {str(e)}")

def parse_receipt_image_to_json(image_path: str, debug=False) -> Dict:
    """
    Single API call: Extract receipt data from image and convert directly to structured JSON
    Combines OCR and JSON extraction in one Gemini Vision API call
    """
    try:
        if not os.path.isfile(image_path):
            return {"status": "error", "msg": f"Image path invalid or does not exist: {image_path}"}

        # Load and process image with Gemini Vision
        image = Image.open(image_path)
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Combined prompt for OCR + JSON extraction in single call
        combined_prompt = """
        You are a receipt parsing assistant for a digital wallet system.
        
        Analyze this receipt image and extract the data directly into structured JSON format.
        
        Extract the following structured fields:
        
        - items: List of objects, each with:
            - name (string): Product/item name
            - quantity (number or unit): Quantity purchased  
            - rate (string): Price per unit
            - value (string): Total price for that item
        
        - summary:
            - gross_total (string): Sum before savings and taxes
            - savings (string): Total savings/discounts (use "0.00" if none)
            - taxes (string): Total of all taxes
            - total_paid (string): Final amount paid
            - date (string): Purchase date in DD-MM-YYYY format
            - store_name (string): Store name and location
        
        Return ONLY valid JSON in this exact format:
        {
            "items": [
                {
                    "name": "Product Name",
                    "quantity": 1,
                    "rate": "10.00",
                    "value": "10.00"
                }
            ],
            "summary": {
                "gross_total": "100.00",
                "savings": "5.00",
                "taxes": "8.00",
                "total_paid": "103.00",
                "date": "25-01-2025",
                "store_name": "Store Name Location"
            }
        }
        
        Be thorough in reading all text from the image. If any field is not clearly visible, use appropriate defaults.
        """
        
        # Single API call for both OCR and JSON extraction
        response = model.generate_content([combined_prompt, image])
        
        if not response.text or not response.text.strip():
            return {"status": "error", "msg": "No readable data found in image."}
            
        raw = response.text.strip()
        
        # Clean up common markdown formatting
        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").strip()
        if raw.endswith("```"):
            raw = raw.removesuffix("```").strip()
            
        if debug:
            print("\n[DEBUG Gemini Combined Output]\n", response.text)
            
        try:
            parsed = json.loads(raw)
            return {"status": "success", "json": parsed, "image": image_path}
        except json.JSONDecodeError as e:
            return {
                "status": "error", 
                "msg": f"JSON parsing failed: {str(e)}", 
                "raw_output": response.text
            }
            
    except Exception as e:
        return {"status": "error", "msg": f"Gemini Vision API error: {str(e)}"}

def parse_receipt_agent(image_source: str, is_url: bool = False) -> Dict:
    """
    Complete flow: Download (if URL) ➜ Single API Call (OCR + JSON) ➜ Structured JSON
    
    Args:
        image_source: Either local file path or public bucket URL
        is_url: True if image_source is a URL, False if local path
    """
    try:
        # Handle URL download
        if is_url:
            print(f"Downloading image from: {image_source}")
            image_path = download_image_from_public_bucket(image_source)
            print(f"Downloaded to: {image_path}")
        else:
            image_path = image_source
            
        # Single API call for OCR + JSON extraction
        result = parse_receipt_image_to_json(image_path, debug=True)
        if result["status"] != "success":
            return {
                "status": "error",
                "msg": result["msg"],
                "raw_output": result.get("raw_output", "")
            }
            
        parsed_json = result["json"]
        
        # Return structured result with same format as before
        return {
            "items": parsed_json.get("items", []),
            "summary": parsed_json.get("summary", {
                "gross_total": "0.00",
                "savings": "0.00", 
                "taxes": "0.00",
                "total_paid": "0.00",
                "date": "01-01-1970",
                "store_name": "Unknown Store"
            }),
            "qr_link": image_source if is_url else f"file://{os.path.abspath(image_path)}",
            "link": f"https://example.com/receipts/{os.path.basename(image_path)}",
            "status": "success"
        }
        
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# ===== CONVENIENCE FUNCTIONS =====
def parse_receipt_from_file(image_path: str) -> Dict:
    """
    Convenience function: Parse receipt from local file path
    Single API call approach
    """
    return parse_receipt_agent(image_path, is_url=False)

def parse_receipt_from_url(image_url: str) -> Dict:
    """
    Convenience function: Parse receipt from public URL
    Single API call approach
    """
    return parse_receipt_agent(image_url, is_url=True)

# 🧪 Example usage
if __name__ == "__main__":
    # Test with local file using new single API call approach
    print("Testing single API call approach with local file...")
    result = parse_receipt_from_file("./Dmart.jpg")
    
    if result["status"] == "success":
        print("\n📦 Parsed JSON (Single API Call):\n", json.dumps(result, indent=2))
        print(f"\n✅ Successfully parsed {len(result['items'])} items")
        print(f"🏪 Store: {result['summary']['store_name']}")
        print(f"💰 Total: ₹{result['summary']['total_paid']}")
    else:
        print("\n❌ Parsing failed:", result["msg"])
        if "raw_output" in result:
            print("Gemini output:\n", result["raw_output"])
    
    # Test with public bucket URL (example)
    # print("\nTesting with public bucket URL...")
    # bucket_url = "https://storage.googleapis.com/your-public-bucket/receipt.jpg"
    # result = parse_receipt_from_url(bucket_url)
    # print(json.dumps(result, indent=2))