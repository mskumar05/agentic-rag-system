# 🚀 Quick Start Guide

Get the Agentic RAG system running in 5 minutes!

## Prerequisites

- Python 3.9+ installed
- pip or conda available
- Internet connection (for downloading dependencies)

## Installation Steps

### 1. Navigate to the project directory
```bash
cd agentic_rag_implementation
```

### 2. Create and activate virtual environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Mac/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

This will install:
- FastAPI and Uvicorn (web framework)
- PyPDF2 and pdfplumber (PDF processing)
- sentence-transformers (embeddings)
- groq (LLM API)
- rank-bm25 (keyword search)
- And other required packages

**Note:** This may take 2-5 minutes depending on your internet speed.

### 4. Start the server
```bash
python -m app.main
```

Or with uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting Agentic RAG System
```

### 5. Open your browser

Navigate to: **http://localhost:8000**

## First Time Usage

### Step 1: Upload PDF Documents
1. Click the upload area or drag PDF files
2. Click "Upload PDFs"
3. Wait for processing (you'll see progress)
4. Check the stats showing documents and chunks

### Step 2: Ask Questions
1. Type a question in the chat input
2. Press Enter or click Send
3. View the answer with citations
4. Toggle "Show reasoning steps" to see the agent's thought process

## Example Questions to Try

Once you've uploaded some PDFs, try:

- "What is the main topic of these documents?"
- "Summarize the key points"
- "List the important concepts mentioned"
- "What are the differences between X and Y?"
- "Define [specific term from your documents]"

## Configuration

Settings are in `.env`:

```env
# Already configured with working Groq API key
GROQ_API_KEY=gsk_tMxftbcwPb1DdtXQUyZWGdyb3FYcuJdWAYYiPLsM8RyLbobOIXH

# Adjust these if needed:
CHUNK_SIZE=512          # Size of text chunks
CHUNK_OVERLAP=50        # Overlap between chunks
TOP_K=5                 # Number of results to retrieve
SIMILARITY_THRESHOLD=0.7 # Minimum similarity for answers
```

## API Testing

### Upload a PDF via cURL:
```bash
curl -X POST "http://localhost:8000/ingest/upload" \
  -F "files=@path/to/your/document.pdf"
```

### Query via cURL:
```bash
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this document about?",
    "top_k": 5,
    "include_citations": true
  }'
```

### Check stats:
```bash
curl "http://localhost:8000/ingest/stats"
```

## Troubleshooting

### "Module not found" error
```bash
# Make sure you're in the virtual environment
# Re-install dependencies
pip install -r requirements.txt
```

### "Port already in use"
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

### PDF upload fails
- Ensure PDF is not corrupted
- Check PDF is not password-protected
- Try with a different PDF

### No answer generated
- Check if documents were uploaded successfully
- Look at `/ingest/stats` endpoint
- Check the server logs for errors

## Features Checklist

Test all features:
- ✅ Upload multiple PDFs
- ✅ View document statistics
- ✅ Ask questions and get answers
- ✅ See citations with page numbers
- ✅ View reasoning steps
- ✅ Adjust retrieval settings
- ✅ Clear documents
- ✅ Try greetings (should respond without searching)

## What's Happening Behind the Scenes?

When you upload PDFs:
1. Text is extracted using pdfplumber/PyPDF2
2. Text is split into overlapping chunks
3. Embeddings are generated using sentence-transformers
4. Chunks and embeddings stored in custom vector store

When you ask a question:
1. **Intent Detection**: Is this a real question?
2. **Query Transformation**: Enhance query for better retrieval
3. **Hybrid Search**: Semantic (vectors) + Keyword (BM25)
4. **Re-ranking**: Score and sort results
5. **Validation**: Check if evidence is sufficient
6. **Generation**: LLM creates answer from context
7. **Verification**: Check for hallucinations
8. **Response**: Return answer with citations

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore the API docs at http://localhost:8000/docs
3. Check the code organization in the [README.md](README.md#project-structure)
4. Test with your own PDF documents
5. Experiment with different settings

## Support

If you encounter issues:
1. Check the terminal/console for error messages
2. Review the troubleshooting section above
3. Ensure all dependencies are installed correctly
4. Try with a fresh virtual environment

---

**Ready to explore?** Upload some PDFs and start asking questions! 🎉
