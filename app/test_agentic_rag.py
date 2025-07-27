# test_agentic_rag.py - Test script for the agentic RAG system

import os
import sys
import asyncio
from pathlib import Path

# Add app to path
current_dir = Path(__file__).parent
app_path = current_dir / "app"
sys.path.insert(0, str(app_path))

async def test_rag_tools():
    """Test the RAG tools functionality"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import tools
        from jarvis.tools.rag_tools import (
            query_receipts_function,
            semantic_search_function,
            add_receipt_function
        )
        
        print("🧪 Testing Agentic RAG System")
        print("=" * 50)
        
        # Test 1: Query recent purchases
        print("\n1. Testing recent purchases query...")
        result1 = query_receipts_function("What did I buy in the last week?")
        print(f"Result: {result1[:200]}...")
        
        # Test 2: Query specific merchant
        print("\n2. Testing merchant-specific query...")
        result2 = query_receipts_function("What did I buy from Big Bazaar?")
        print(f"Result: {result2[:200]}...")
        
        # Test 3: Query specific item
        print("\n3. Testing item-specific query...")
        result3 = query_receipts_function("Did I buy milk recently?")
        print(f"Result: {result3[:200]}...")
        
        # Test 4: Semantic search
        print("\n4. Testing semantic search...")
        result4 = semantic_search_function("What is Firebase?")
        print(f"Result: {result4[:200]}...")
        
        # Test 5: Add new receipt
        print("\n5. Testing add receipt...")
        new_receipt = {
            "receipt_id": "test_receipt_001",
            "uid": "user_001",
            "timestamp": "2025-07-27T12:00:00",
            "merchant": "Test Store",
            "category_summary": {"test": 100.0},
            "items": [{"name": "Test Item", "category": "test", "amount": 100}]
        }
        result5 = add_receipt_function(str(new_receipt).replace("'", '"'))
        print(f"Result: {result5}")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_agent_initialization():
    """Test agent initialization"""
    try:
        from jarvis.agent import root_agent
        print(f"✅ Agent initialized: {root_agent.name}")
        print(f"   Description: {root_agent.description}")
        print(f"   Tools: {len(root_agent.tools)} tools available")
        for tool in root_agent.tools:
            print(f"   - {tool.name}: {tool.description}")
        return True
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Agentic RAG Tests")
    
    # Test agent initialization
    if test_agent_initialization():
        # Test RAG tools
        asyncio.run(test_rag_tools())
    else:
        print("❌ Cannot proceed with tool tests - agent initialization failed")