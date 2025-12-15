# 🍎 macOS Setup Guide - Agentic RAG System

Complete guide to set up and run the Agentic RAG system on macOS.

---

## 📋 Prerequisites

- **macOS**: 10.15 (Catalina) or newer
- **Python**: 3.9 or higher (tested with 3.13.7)
- **RAM**: 8GB minimum, 16GB+ recommended
- **Disk Space**: ~20GB free space

## ✅ Already Completed Setup

If you're reading this and your environment is already set up (virtual environment created, dependencies installed), skip to [Running the System](#-running-the-system).

---

## 🚀 Quick Start (5 Steps)

### Step 1: Install Homebrew (if not installed)

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Verify installation
brew --version
```

---

### Step 2: Install Python 3.9+

```bash
# Install Python via Homebrew
brew install python@3.11

# Verify installation
python3 --version
# Should show: Python 3.11.x

# Create alias (add to ~/.zshrc or ~/.bash_profile)
echo 'alias python=python3' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc
source ~/.zshrc
```

---

### Step 3: Install Ollama and Models

#### Install Ollama
```bash
# Download and install Ollama
brew install ollama

# OR download directly from website
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

#### Start Ollama Service
```bash
# Start Ollama server (runs in background)
ollama serve

# OR run in a separate terminal
# Keep this terminal open while using the RAG system
```

#### Install Required Models
```bash
# Open a NEW terminal window (keep ollama serve running)

# Install Mistral LLM (7B model, ~4GB download)
ollama pull mistral

# Install Nomic Embed Text (embedding model, ~274MB download)
ollama pull nomic-embed-text

# Verify models are installed
ollama list

# Expected output:
# NAME                    ID              SIZE
# mistral:latest          abc123...       4.1 GB
# nomic-embed-text:latest def456...       274 MB
```

---

### Step 4: Setup Python Environment

```bash
# Navigate to the project directory
cd /path/to/agentic_rag_implementation

# Create virtual environment (use .venv for consistency)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This will install ~30+ packages including:
# - FastAPI, Uvicorn (web framework)
# - PyMuPDF, pdfplumber, PyPDF2 (PDF processing)
# - sentence-transformers (embeddings support)
# - numpy, scikit-learn (ML utilities)
# - And more...

# Download NLTK data (required for text processing)
python -c "
import ssl
import nltk
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt_tab')
"
```

**Note**: First installation may take 5-10 minutes depending on internet speed. Python 3.13 is supported.

---

### Step 5: Configure Environment Variables

```bash
# The .env file should already be in the project
# Verify it exists
cat .env

# Should show:
# EMBEDDING_PROVIDER=ollama
# EMBEDDING_MODEL=nomic-embed-text
# LLM_PROVIDER=ollama
# LLM_MODEL=mistral
# ... etc

# If .env doesn't exist, create it:
cat > .env << 'EOF'
# LLM API Keys (optional - not used with Ollama)
GROQ_API_KEY=your_key_here
MISTRAL_API_KEY=
TOGETHER_API_KEY=

# Application Settings
APP_NAME=Agentic RAG System
DEBUG=True
HOST=0.0.0.0
PORT=8000

# RAG Settings
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K=5
SIMILARITY_THRESHOLD=0.45
MAX_CONTEXT_LENGTH=4096

# Embedding Settings (Ollama - Local)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# LLM Settings (Ollama - Local)
LLM_PROVIDER=ollama
LLM_MODEL=mistral
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.3
MAX_TOKENS=2048
EOF
```

---

## 🎯 Running the System

### Start the Server

```bash
# Make sure you're in the project directory with venv activated
cd /path/to/agentic_rag_implementation
source .venv/bin/activate

# Make sure Ollama is running (check with: ollama list)

# Start the FastAPI server
.venv/bin/python -m app.main

# OR use uvicorn directly:
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Expected output:
# INFO: Starting Agentic RAG System
# INFO: Debug mode: True
# INFO: LLM Provider: ollama
# INFO: LLM Model: mistral
# INFO: Uvicorn running on http://0.0.0.0:8000
# INFO: Application startup complete.
```

### Access the System

**Web UI**: Open your browser and go to:
```
http://localhost:8000
```

**API Documentation**: Interactive API docs at:
```
http://localhost:8000/docs
```

---

## 🧪 Testing the System

### Test 1: Health Check
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","app":"Agentic RAG System","version":"1.0.0"}
```

### Test 2: Upload a PDF
```bash
# Upload Resume_in.pdf (if you have it in the directory)
curl -X POST "http://localhost:8000/ingest/upload" \
  -F "files=@Resume_in.pdf"

# Expected: {"success":true,"message":"Successfully processed 1 PDF(s)",...}
```

### Test 3: Query the System
```bash
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the candidate education?",
    "top_k": 5,
    "include_citations": true
  }'

# Should return a JSON response with answer and citations
```

### Test 4: Check Statistics
```bash
curl http://localhost:8000/ingest/stats

# Expected: {"success":true,"total_chunks":10,"total_documents":1,...}
```

---

## 📁 Directory Structure

```
agentic_rag_implementation/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Core functionality
│   ├── models/           # Pydantic schemas
│   ├── services/         # Business logic
│   └── utils/            # Helper functions
├── ui/                   # Web interface
├── data/                 # Data storage (created on first run)
│   ├── uploads/          # Uploaded PDFs
│   └── vector_db/        # Vector embeddings
├── .env                  # Environment configuration
├── requirements.txt      # Python dependencies
├── README.md             # Documentation
├── SETUP_MAC.md          # This file
└── venv/                 # Virtual environment (after setup)
```

---

## 🔧 Troubleshooting

### Issue: Ollama Not Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not working, start Ollama
ollama serve

# Run in a separate terminal or use background process:
nohup ollama serve > ollama.log 2>&1 &
```

### Issue: Model Not Found
```bash
# List installed models
ollama list

# If mistral or nomic-embed-text is missing, install:
ollama pull mistral
ollama pull nomic-embed-text
```

### Issue: Port 8000 Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process (replace PID with actual number)
kill -9 PID

# Or use a different port
# Edit .env and change PORT=8001
# Then restart the server
```

### Issue: Python Version Too Old
```bash
# Check Python version
python3 --version

# If < 3.9, install newer version
brew install python@3.11

# Update your PATH in ~/.zshrc
export PATH="/opt/homebrew/bin:$PATH"
source ~/.zshrc
```

### Issue: Permission Denied
```bash
# If you get permission errors, fix with:
chmod -R 755 /path/to/agentic_rag_implementation

# Or run with sudo (not recommended)
sudo python -m app.main
```

### Issue: Virtual Environment Not Activating
```bash
# Delete and recreate venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🎨 Optional: Install Additional Tools

### Install Git (if not already installed)
```bash
brew install git

# Verify
git --version
```

### Install VS Code (optional)
```bash
brew install --cask visual-studio-code

# Or download from: https://code.visualstudio.com
```

### Install HTTPie (better than curl)
```bash
brew install httpie

# Test with:
http http://localhost:8000/api/health
```

---

## 🔐 Security Notes

### API Keys
- The `.env` file contains API keys (if using Groq/Mistral API)
- **Never commit** `.env` to version control
- The `.gitignore` already excludes it

### Firewall
- The server binds to `0.0.0.0:8000` (all interfaces)
- For production, change to `127.0.0.1:8000` (localhost only)
- Edit `.env`: `HOST=127.0.0.1`

---

## 📊 Performance Tips

### Optimize for Mac M1/M2 (Apple Silicon)
```bash
# Install native ARM versions
arch -arm64 brew install python@3.11
arch -arm64 brew install ollama

# Use Metal acceleration (automatic with Ollama on M1/M2)
# Ollama will automatically use GPU acceleration
```

### Increase Performance
```bash
# Use smaller models for faster responses (optional)
ollama pull mistral:7b-instruct-q4_0  # Quantized version

# Reduce max tokens in .env
MAX_TOKENS=1024  # Instead of 2048
```

---

## 🚫 What NOT to Do

❌ **Don't** commit the `data/` folder to Git (contains uploaded files)
❌ **Don't** commit the `venv/` folder (virtual environment)
❌ **Don't** commit the `.env` file (contains API keys)
❌ **Don't** run with `sudo` unless absolutely necessary
❌ **Don't** use the same virtual environment across different projects

---

## ✅ Quick Commands Reference

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Start Ollama
ollama serve

# Check Ollama models
ollama list

# Start RAG server
python -m app.main

# Run in background
nohup python -m app.main > rag.log 2>&1 &

# Stop background server
pkill -f "python -m app.main"

# View logs
tail -f rag.log

# Clear vector database
curl -X DELETE "http://localhost:8000/ingest/clear"
```

---

## 📦 Packaging for Transfer

### Create a Clean Package (before zipping)
```bash
# Clean up unnecessary files
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
rm -rf venv/
rm -rf data/vector_db/*.pkl
rm -rf .pytest_cache/

# Create zip file (excluding unnecessary files)
zip -r agentic_rag_system.zip . \
  -x "*.pyc" \
  -x "*__pycache__*" \
  -x "*venv*" \
  -x "*.pkl" \
  -x ".git/*" \
  -x "data/uploads/*" \
  -x "data/vector_db/*"
```

### After Extracting on Mac
```bash
# Extract the zip
unzip agentic_rag_system.zip -d agentic_rag_implementation
cd agentic_rag_implementation

# Follow steps 1-5 from Quick Start above
# Then you're ready to go!
```

---

## 🎓 Next Steps

1. ✅ Install Ollama and models
2. ✅ Setup Python environment
3. ✅ Start the server
4. ✅ Upload your first PDF
5. ✅ Test queries via UI or API
6. 📖 Read the [README.md](README.md) for detailed documentation
7. 📖 Check [TASK3_IMPLEMENTATION.md](TASK3_IMPLEMENTATION.md) for architecture details

---

## 💡 Tips for Mac Users

### Use iTerm2 (Better Terminal)
```bash
brew install --cask iterm2
```

### Create Aliases (add to ~/.zshrc)
```bash
# Quick aliases for this project
alias rag-activate='cd /path/to/agentic_rag_implementation && source venv/bin/activate'
alias rag-start='rag-activate && python -m app.main'
alias rag-stop='pkill -f "python -m app.main"'
alias rag-logs='tail -f rag.log'
alias ollama-start='ollama serve'

# Apply changes
source ~/.zshrc
```

### Monitor Resources
```bash
# Monitor CPU/Memory usage
top

# Or use Activity Monitor (GUI)
open -a "Activity Monitor"
```

---

## 🆘 Getting Help

**Issues?** Check:
1. Ollama is running: `curl http://localhost:11434/api/tags`
2. Python version: `python3 --version` (need 3.9+)
3. Virtual environment: `which python` (should point to venv)
4. Dependencies: `pip list | grep fastapi`
5. Logs: Check terminal output or `rag.log`

**Still stuck?**
- Check the main [README.md](README.md)
- Review [TASK3_IMPLEMENTATION.md](TASK3_IMPLEMENTATION.md)
- Ensure all models are downloaded: `ollama list`

---

## ✨ You're All Set!

The system is now ready to use on macOS. Enjoy your 100% local RAG system! 🎉

**Default Access**:
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health
