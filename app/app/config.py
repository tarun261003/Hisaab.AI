# config.py - Configuration for the agentic RAG system

import os
import sys
from pathlib import Path

# Add RAG module to Python path
current_dir = Path(__file__).parent
rag_path = current_dir.parent.parent / "rag"
sys.path.insert(0, str(rag_path))

# Environment variables check
def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        "GOOGLE_API_KEY",
        "FIREBASE_SERVICE_ACCOUNT_PATH"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables for full RAG functionality.")
        return False
    
    return True

def initialize_rag_system():
    """Initialize the RAG system components"""
    try:
        # Check environment
        if not check_environment():
            return False
        
        # Initialize Google API
        from google.generativeai import configure
        configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Test Firebase connection
        firebase_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if firebase_path and os.path.exists(firebase_path):
            print("RAG system initialized successfully")
            return True
        else:
            print("Firebase service account path not found")
            return False
            
    except Exception as e:
        print(f"Error initializing RAG system: {e}")
        return False

# Initialize on import
RAG_INITIALIZED = initialize_rag_system()