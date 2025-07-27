# rag_tools.py - RAG tools for the ADK agent

import os
import sys
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Add the rag module to the path
rag_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'rag')
sys.path.append(rag_path)

from rag.data_handler import (
    generate_text_embedding,
    retrieve_relevant_chunks_rag,
    query_structured_receipt_data,
    parse_time_metric,
    store_receipt_in_firestore
)
from rag.llm_service import generate_response_from_llm
from google.adk.tools import Tool
from google.genai import types
import json

# Initialize Google API for embeddings
from google.generativeai import configure
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    configure(api_key=GOOGLE_API_KEY)

def analyze_query_for_structured_data(user_query: str) -> Optional[Dict]:
    """
    Analyzes user query to determine if it requires structured data retrieval
    """
    from rag.llm_service import llm_model
    
    prompt = f"""
    Analyze the following user query to determine if it asks for specific transaction details.
    Extract relevant parameters in JSON format.
    
    Possible parameters:
    - "uid": (default to 'user_001' if not specified)
    - "time_range": (e.g., "last two weeks", "last week", "today", "yesterday", "last month")
    - "merchant": (e.g., "Big Bazaar", "Food Mart")
    - "category": (e.g., "groceries", "household", "vegetables", "drinks")
    - "item_name": (e.g., "Milk", "Rice", "Apples")

    If the query is general knowledge, return empty JSON {{}}.
    Return only JSON, no other text.

    User Query: "{user_query}"
    """

    try:
        response = llm_model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        extracted_params = json.loads(json_str)
        
        if "uid" not in extracted_params:
            extracted_params["uid"] = "user_001"
            
        return extracted_params if any(k for k in extracted_params if k != "uid") else None
    except Exception as e:
        print(f"Error analyzing query: {e}")
        return None

# Tool for querying receipt data
query_receipts_tool = Tool(
    name="query_receipts",
    description="Query user's receipt and transaction data based on time periods, merchants, categories, or specific items",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "user_query": types.Schema(
                type=types.Type.STRING,
                description="The user's natural language query about their receipts or purchases"
            ),
            "uid": types.Schema(
                type=types.Type.STRING,
                description="User ID (defaults to 'user_001')",
                default="user_001"
            )
        },
        required=["user_query"]
    )
)

@query_receipts_tool.set_function
def query_receipts_function(user_query: str, uid: str = "user_001") -> str:
    """
    Processes a user query about their receipts and returns relevant information
    """
    try:
        print(f"Processing receipt query: {user_query}")
        
        # Analyze query for structured data parameters
        extracted_params = analyze_query_for_structured_data(user_query)
        
        context_for_llm = ""
        
        if extracted_params:
            print("Structured query detected, retrieving structured data...")
            
            # Parse time range
            start_date, end_date = None, None
            if "time_range" in extracted_params:
                start_date, end_date = parse_time_metric(user_query)
            
            # Query structured data
            receipts = query_structured_receipt_data(
                uid=extracted_params.get("uid", uid),
                start_date=start_date,
                end_date=end_date,
                merchant=extracted_params.get("merchant"),
                category=extracted_params.get("category"),
                item_name=extracted_params.get("item_name"),
                limit=10
            )
            
            if receipts:
                context_for_llm = "Found the following transaction data:\n\n"
                for receipt in receipts:
                    context_for_llm += f"Receipt ID: {receipt.get('receipt_id')}\n"
                    context_for_llm += f"Merchant: {receipt.get('merchant')}\n"
                    context_for_llm += f"Date: {receipt.get('timestamp')}\n"
                    context_for_llm += f"Categories: {receipt.get('category_summary', {})}\n"
                    context_for_llm += f"Items: {[item['name'] + ' (' + str(item['amount']) + ')' for item in receipt.get('items', [])]}\n\n"
        
        # If no structured data found, use semantic search
        if not context_for_llm:
            print("Using semantic search for query...")
            query_embedding = generate_text_embedding(user_query)
            if query_embedding:
                relevant_chunks = retrieve_relevant_chunks_rag(query_embedding, limit=3)
                if relevant_chunks:
                    context_for_llm = "\n\n".join([chunk.get("text", "") for chunk in relevant_chunks])
        
        # Generate response using LLM
        if context_for_llm:
            response = generate_response_from_llm(user_query, context_for_llm)
            return response
        else:
            return "I couldn't find any relevant information about your receipts for that query. Please try asking about specific purchases, time periods, or merchants."
            
    except Exception as e:
        print(f"Error in query_receipts_function: {e}")
        return f"I encountered an error while searching your receipts: {str(e)}"

# Tool for adding new receipt data
add_receipt_tool = Tool(
    name="add_receipt",
    description="Add a new receipt to the user's transaction history",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "receipt_data": types.Schema(
                type=types.Type.STRING,
                description="JSON string containing receipt data with fields: receipt_id, uid, timestamp, merchant, category_summary, items"
            )
        },
        required=["receipt_data"]
    )
)

@add_receipt_tool.set_function
def add_receipt_function(receipt_data: str) -> str:
    """
    Adds a new receipt to the user's data store
    """
    try:
        receipt_dict = json.loads(receipt_data)
        
        # Validate required fields
        required_fields = ["receipt_id", "uid", "timestamp", "merchant", "items"]
        for field in required_fields:
            if field not in receipt_dict:
                return f"Error: Missing required field '{field}' in receipt data"
        
        # Store the receipt
        store_receipt_in_firestore(receipt_dict)
        
        return f"Successfully added receipt {receipt_dict['receipt_id']} from {receipt_dict['merchant']} to your transaction history."
        
    except json.JSONDecodeError:
        return "Error: Invalid JSON format for receipt data"
    except Exception as e:
        return f"Error adding receipt: {str(e)}"

# Tool for general RAG search
semantic_search_tool = Tool(
    name="semantic_search",
    description="Perform semantic search across all stored documents and receipts for general questions",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description="The search query for semantic search"
            )
        },
        required=["query"]
    )
)

@semantic_search_tool.set_function
def semantic_search_function(query: str) -> str:
    """
    Performs semantic search across all stored documents
    """
    try:
        query_embedding = generate_text_embedding(query)
        if not query_embedding:
            return "Failed to generate embedding for your query."
        
        relevant_chunks = retrieve_relevant_chunks_rag(query_embedding, limit=5)
        if not relevant_chunks:
            return "No relevant information found for your query."
        
        context = "\n\n".join([chunk.get("text", "") for chunk in relevant_chunks])
        response = generate_response_from_llm(query, context)
        
        return response
        
    except Exception as e:
        return f"Error performing semantic search: {str(e)}"