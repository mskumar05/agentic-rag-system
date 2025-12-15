# 🚀 Complete Installation Guide - Ollama + Mistral

## System Overview

**100% Local Setup - No API Keys Needed!**
- **LLM**: Ollama → `mistral` (7B parameters, runs locally)
- **Embeddings**: Hugging Face → `intfloat/e5-mistral-7b-instruct` (local)
- **Vector Store**: Custom numpy-based (local)
- **Backend**: FastAPI
- **Everything runs on your machine!**

---

## Step 1: Install Ollama

### Windows
```bash
# Download and install Ollama
curl -o OllamaSetup.exe https://ollama.com/download/OllamaSetup.exe

# Run the installer
./OllamaSetup.exe
```

Or download manually from: https://ollama.com/download/windows

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS
```bash
# Download from website
curl -o Ollama.dmg https://ollama.com/download/Ollama.dmg

# Or use Homebrew
brew install ollama
```

---

## Step 2: Install Mistral Model

After installing Ollama, pull the Mistral model:

```bash
# Pull Mistral 7B model (~4GB download)
ollama pull mistral

# Verify it's installed
ollama list
```

Expected output:
```
NAME            ID              SIZE    MODIFIED
mistral:latest  abc123          4.1 GB  2 minutes ago
```

---

## Step 3: Start Ollama Server

### Windows/Linux/macOS
```bash
# Start Ollama server (runs in background)
ollama serve
```

Keep this terminal open or run in background.

**Verify it's running:**
```bash
curl http://localhost:11434/api/tags
```

Should return JSON with available models.

---

## Step 4: Install Python Dependencies

Navigate to project directory:
```bash
cd agentic_rag_implementation

# Install all dependencies
pip install -r requirements.txt
```

This installs:
- FastAPI
- sentence-transformers (for embeddings)
- All other required packages

---

## Step 5: Start RAG System

```bash
# Start the FastAPI server
python -m app.main
```

**First time:** Will download E5-Mistral embeddings (~15GB)

Expected output:
```
INFO:     Loading Mistral-based embedding model: intfloat/e5-mistral-7b-instruct
INFO:     Note: First time will download ~15GB. Subsequent loads are instant.
Downloading...
INFO:     ✓ Mistral embeddings loaded successfully
INFO:     Embedding dimension: 4096
INFO:     Initialized Ollama client with model: mistral
INFO:     Ollama URL: http://localhost:11434
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 6: Test the System

### 6.1 Upload Resume (via curl)

```bash
# Upload Resume_in.pdf
curl -X POST "http://localhost:8000/ingest/upload" \
  -F "files=@Resume_in.pdf"
```

Expected response:
```json
{
  "success": true,
  "message": "Successfully processed 1 PDF(s)",
  "documents_processed": 1,
  "total_chunks": 45,
  "document_ids": ["doc_abc123"]
}
```

### 6.2 Check Statistics

```bash
curl http://localhost:8000/ingest/stats
```

Response:
```json
{
  "success": true,
  "total_chunks": 45,
  "total_documents": 1,
  "embedding_dim": 4096
}
```

### 6.3 Query the System

```bash
# Ask a question
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What programming languages does the candidate know?",
    "top_k": 5,
    "include_citations": true
  }'
```

Expected response:
```json
{
  "query": "What programming languages does the candidate know?",
  "answer": "Based on the resume, the candidate knows Python, JavaScript, Java...",
  "intent": "question",
  "citations": [
    {
      "document_name": "Resume_in.pdf",
      "page_number": 1,
      "chunk_text": "Skills: Python, JavaScript...",
      "relevance_score": 0.85
    }
  ],
  "confidence": 0.82,
  "has_sufficient_evidence": true,
  "warning": null
}
```

### 6.4 More Test Queries

```bash
# Skills
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What skills does the candidate have?"}'

# Education
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is their educational background?"}'

# Experience
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What work experience do they have?"}'

# Projects
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What projects have they worked on?"}'
```

### 6.5 Test Intent Detection

```bash
# Greeting (should not search KB)
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello!"}'

# Chitchat (should not search KB)
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "Thanks!"}'
```

---

## Step 7: Clear Data (if needed)

```bash
# Clear all documents and start fresh
curl -X DELETE "http://localhost:8000/ingest/clear"
```

---

## All-in-One Test Script

Create `test_all.sh`:

```bash
#!/bin/bash

echo "🧪 Testing Agentic RAG System with Ollama"
echo "=========================================="

echo ""
echo "📊 Step 1: Check server health"
curl -s http://localhost:8000/api/health | python -m json.tool

echo ""
echo "📤 Step 2: Upload Resume_in.pdf"
curl -s -X POST "http://localhost:8000/ingest/upload" \
  -F "files=@Resume_in.pdf" | python -m json.tool

echo ""
echo "📊 Step 3: Check stats"
curl -s http://localhost:8000/ingest/stats | python -m json.tool

echo ""
echo "❓ Step 4: Test questions"

echo ""
echo "Q1: What programming languages does the candidate know?"
curl -s -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What programming languages does the candidate know?", "top_k": 3}' \
  | python -m json.tool

echo ""
echo "Q2: What skills does the candidate have?"
curl -s -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What skills does the candidate have?"}' \
  | python -m json.tool

echo ""
echo "✅ Testing complete!"
```

Run it:
```bash
chmod +x test_all.sh
./test_all.sh
```

---

## Troubleshooting

### Ollama not running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model not found
```bash
# List installed models
ollama list

# Pull Mistral if missing
ollama pull mistral
```

### Server not starting
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000    # Windows
lsof -i :8000                    # Linux/Mac

# Use different port
uvicorn app.main:app --port 8001
```

### Slow response times
- First query is slower (model loading)
- Subsequent queries are faster
- Consider using smaller model: `ollama pull mistral:7b-instruct-q4_0`

---

## System Requirements

### Disk Space
- Ollama: ~500MB
- Mistral model: ~4GB
- E5-Mistral embeddings: ~15GB
- **Total: ~20GB**

### RAM
- **Minimum**: 8GB
- **Recommended**: 16GB
- **Optimal**: 32GB

### CPU/GPU
- CPU: Works fine (slower inference)
- GPU: Much faster (optional)

---

## Performance Notes

| Operation | Time (CPU) | Time (GPU) |
|-----------|-----------|-----------|
| Embedding generation | ~5 sec/100 chunks | ~1 sec/100 chunks |
| LLM response | ~10-30 sec | ~2-5 sec |
| First query | Slower (loading) | Slower (loading) |
| Subsequent queries | Fast | Very fast |

---

## Web UI Access

Open browser:
```
http://localhost:8000
```

Features:
- Drag & drop PDF upload
- Real-time chat interface
- Citation display
- Reasoning steps visualization
- Confidence scoring

---

## API Documentation

Interactive API docs:
```
http://localhost:8000/docs
```

---

## Quick Commands Reference

```bash
# Ollama
ollama serve                     # Start Ollama server
ollama list                      # List installed models
ollama pull mistral              # Download Mistral
ollama rm mistral                # Remove model

# RAG System
python -m app.main               # Start server
python test_resume.py            # Run automated tests

# API Testing
curl http://localhost:8000/api/health                    # Health check
curl -X POST .../ingest/upload -F "files=@file.pdf"     # Upload
curl -X POST .../query/ -d '{"query": "..."}'           # Query
curl -X DELETE .../ingest/clear                          # Clear all

# Ollama Direct Testing
ollama run mistral "What is Python?"                     # Test Ollama
```

---

## Benefits of This Setup

✅ **100% Local** - No API keys, no cloud dependencies
✅ **Free** - No costs for LLM or embeddings
✅ **Private** - Your data never leaves your machine
✅ **Fast** - Ollama optimized for local inference
✅ **Consistent** - Both LLM and embeddings use Mistral

---

## Next Steps

1. ✅ Ollama installed and running
2. ✅ Mistral model downloaded
3. ✅ Python dependencies installed
4. ✅ RAG server started
5. ✅ Resume uploaded and tested

**You're ready to use the system!** 🎉

Try it with your own PDFs or explore the web UI at http://localhost:8000
