# Agentic RAG Assistant

An intelligent conversational AI system that combines Retrieval-Augmented Generation (RAG) with real-time chat capabilities for querying receipt and transaction data.

## Features

### 🧠 Intelligent Query Processing

- **Structured Queries**: Ask about specific purchases, time periods, merchants, or categories
- **Semantic Search**: Natural language search across all stored documents and receipts
- **Context-Aware Responses**: Get relevant, accurate answers based on your actual transaction data

### 💬 Real-Time Conversation

- **WebSocket-based Chat**: Real-time streaming responses
- **Voice Support**: Audio input and output capabilities
- **Multi-modal Interface**: Text and voice interaction

### 📊 Receipt Management

- **Automatic Data Processing**: Store and organize receipt data with embeddings
- **Smart Categorization**: Automatic categorization of purchases
- **Time-based Queries**: Search by date ranges, recent purchases, etc.

## Setup

### Prerequisites

1. **Google API Key**: For Gemini AI and embeddings
2. **Firebase Project**: With Firestore database enabled
3. **Service Account**: Firebase service account key file

### Environment Variables

Create a `.env` file in the `app/` directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/your/serviceAccountKey.json
```

### Installation

```bash
cd app
pip install -r requirements.txt
```

### Running the Application

```bash
cd app
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`

## Usage Examples

### Receipt Queries

- "What did I buy last week?"
- "How much did I spend at Big Bazaar?"
- "What groceries do I have from recent purchases?"
- "Did I buy milk recently?"
- "Show me all my purchases from yesterday"
- "What can I cook with ingredients I bought in the last two weeks?"

### Category-based Queries

- "What household items did I purchase?"
- "Show me all my grocery expenses this month"
- "What health products did I buy?"

### Merchant-specific Queries

- "What did I buy from Food Mart?"
- "How much have I spent at the Coffee Shop?"
- "Show me all purchases from Local Pharmacy"

### General Questions

- "What is Firebase?" (uses semantic search)
- "How does RAG work?" (searches general knowledge base)

## Architecture

### Components

1. **ADK Agent**: Google's Agent Development Kit for conversational AI
2. **RAG Tools**: Custom tools for receipt querying and semantic search
3. **Firebase Integration**: Firestore for data storage and retrieval
4. **Embedding System**: Google's text-embedding-004 for semantic search
5. **WebSocket Interface**: Real-time communication between client and server

### Data Flow

1. User sends query via WebSocket
2. Agent analyzes query intent (structured vs semantic)
3. Appropriate tool is called (receipt query or semantic search)
4. Data is retrieved from Firestore
5. LLM generates contextual response
6. Response is streamed back to user

### Tools Available to Agent

- `query_receipts`: Query receipt data with filters
- `add_receipt`: Add new receipts to the system
- `semantic_search`: Perform semantic search across documents

## API Endpoints

### WebSocket

- `ws://localhost:8000/ws/{session_id}?is_audio=false` - Text chat
- `ws://localhost:8000/ws/{session_id}?is_audio=true` - Voice chat

### HTTP

- `GET /` - Serves the web interface
- `GET /static/*` - Static files

## Sample Data

The system automatically initializes with sample receipt data including:

- Grocery purchases from Big Bazaar and Food Mart
- Health products from Local Pharmacy
- Food purchases from Coffee Shop
- Various categories: groceries, household, health, personal care, snacks

## Customization

### Adding New Tools

Create new tools in `app/jarvis/tools/` and register them in `agent.py`

### Modifying Agent Behavior

Update the agent instructions in `app/jarvis/agent.py`

### Extending Data Sources

Add new data handlers in the RAG system and create corresponding tools

## Troubleshooting

### Common Issues

1. **Firebase Connection**: Ensure service account path is correct
2. **API Keys**: Verify Google API key has necessary permissions
3. **Dependencies**: Install all requirements including Firebase Admin SDK
4. **Data Initialization**: Check if sample data was loaded successfully

### Logs

The system provides detailed logging for:

- RAG system initialization
- Query processing
- Tool execution
- Firebase operations

## Development

### Project Structure

```
app/
├── app/
│   ├── jarvis/
│   │   ├── agent.py          # Main agent configuration
│   │   └── tools/
│   │       └── rag_tools.py  # RAG-specific tools
│   ├── static/               # Web interface files
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and initialization
│   └── initialize_sample_data.py  # Sample data setup
├── requirements.txt
└── README.md
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is part of the Hisab.AI ecosystem for intelligent expense tracking and management.
