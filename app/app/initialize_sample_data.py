# initialize_sample_data.py - Initialize sample receipt data for the agentic RAG system

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add RAG module to path
current_dir = Path(__file__).parent
rag_path = current_dir.parent.parent / "rag"
sys.path.insert(0, str(rag_path))

def initialize_sample_receipts():
    """Initialize sample receipt data if none exists"""
    try:
        from rag.data_handler import store_receipt_in_firestore, query_structured_receipt_data
        from google.generativeai import configure
        
        # Configure API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("GOOGLE_API_KEY not set, skipping sample data initialization")
            return False
            
        configure(api_key=api_key)
        
        # Check if data already exists
        existing_receipts = query_structured_receipt_data(uid="user_001", limit=1)
        if existing_receipts:
            print("Sample receipt data already exists, skipping initialization")
            return True
        
        # Create sample data
        now = datetime.now()
        sample_receipts = [
            {
                "receipt_id": "r001_agentic",
                "uid": "user_001",
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "merchant": "Big Bazaar",
                "category_summary": {"groceries": 850.0, "household": 120.0},
                "items": [
                    {"name": "Milk", "category": "groceries", "amount": 60},
                    {"name": "Bread", "category": "groceries", "amount": 40},
                    {"name": "Rice", "category": "groceries", "amount": 500},
                    {"name": "Eggs", "category": "groceries", "amount": 120},
                    {"name": "Tomatoes", "category": "groceries", "amount": 80},
                    {"name": "Onions", "category": "groceries", "amount": 50},
                    {"name": "Dish Soap", "category": "household", "amount": 120}
                ]
            },
            {
                "receipt_id": "r002_agentic",
                "uid": "user_001",
                "timestamp": (now - timedelta(days=5)).isoformat(),
                "merchant": "Food Mart",
                "category_summary": {"groceries": 450.0, "snacks": 80.0},
                "items": [
                    {"name": "Chicken", "category": "groceries", "amount": 300},
                    {"name": "Pasta", "category": "groceries", "amount": 150},
                    {"name": "Chips", "category": "snacks", "amount": 80}
                ]
            },
            {
                "receipt_id": "r003_agentic",
                "uid": "user_001",
                "timestamp": (now - timedelta(days=10)).isoformat(),
                "merchant": "Local Pharmacy",
                "category_summary": {"health": 200.0, "personal_care": 150.0},
                "items": [
                    {"name": "Vitamins", "category": "health", "amount": 200},
                    {"name": "Shampoo", "category": "personal_care", "amount": 150}
                ]
            },
            {
                "receipt_id": "r004_agentic",
                "uid": "user_001",
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "merchant": "Coffee Shop",
                "category_summary": {"food": 180.0},
                "items": [
                    {"name": "Latte", "category": "food", "amount": 120},
                    {"name": "Sandwich", "category": "food", "amount": 60}
                ]
            }
        ]
        
        # Store sample receipts
        for receipt in sample_receipts:
            store_receipt_in_firestore(receipt)
            
        print(f"✅ Initialized {len(sample_receipts)} sample receipts")
        return True
        
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        return False

if __name__ == "__main__":
    initialize_sample_receipts()