#!/bin/bash

# 🚀 Quick Start Script for macOS
# Agentic RAG System

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Agentic RAG System - macOS Launcher  ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if Ollama is running
echo -e "${YELLOW}[1/4]${NC} Checking Ollama service..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${RED}✗ Ollama is not running!${NC}"
    echo -e "${YELLOW}Please start Ollama first:${NC}"
    echo -e "  ${GREEN}ollama serve${NC}"
    echo -e "\nOr run in background:"
    echo -e "  ${GREEN}nohup ollama serve > ollama.log 2>&1 &${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama is running${NC}\n"

# Check if models are installed
echo -e "${YELLOW}[2/4]${NC} Checking required models..."
if ! ollama list | grep -q "mistral"; then
    echo -e "${RED}✗ Mistral model not found!${NC}"
    echo -e "${YELLOW}Installing mistral model...${NC}"
    ollama pull mistral
fi

if ! ollama list | grep -q "nomic-embed-text"; then
    echo -e "${RED}✗ Nomic embed text model not found!${NC}"
    echo -e "${YELLOW}Installing nomic-embed-text model...${NC}"
    ollama pull nomic-embed-text
fi
echo -e "${GREEN}✓ All models are installed${NC}\n"

# Activate virtual environment
echo -e "${YELLOW}[3/4]${NC} Activating virtual environment..."
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Virtual environment not found!${NC}"
    echo -e "${YELLOW}Run setup first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}\n"

# Start the server
echo -e "${YELLOW}[4/4]${NC} Starting the RAG server..."
echo -e "${GREEN}✓ Server is starting...${NC}\n"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Access the system at:${NC}"
echo -e "  ${BLUE}http://localhost:8000${NC}"
echo -e ""
echo -e "${GREEN}API Documentation:${NC}"
echo -e "  ${BLUE}http://localhost:8000/docs${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Start the application
exec .venv/bin/python -m app.main
