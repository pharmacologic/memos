#!/bin/bash
# Setup script for voice memo analysis

set -e

echo "Setting up voice memo analysis pipeline..."

# Default Ollama settings
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_API_BASE="http://${OLLAMA_HOST}:${OLLAMA_PORT}/api"

# Allow user to specify Ollama server
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [OLLAMA_HOST] [OLLAMA_PORT]"
    echo
    echo "Examples:"
    echo "  $0                    # Use localhost:11434"
    echo "  $0 192.168.1.100      # Use 192.168.1.100:11434"
    echo "  $0 ollama.local 8080  # Use ollama.local:8080"
    echo
    echo "Environment variables:"
    echo "  OLLAMA_HOST=hostname  # Default: localhost"
    echo "  OLLAMA_PORT=port      # Default: 11434"
    exit 0
fi

if [ -n "$1" ]; then
    OLLAMA_HOST="$1"
fi

if [ -n "$2" ]; then
    OLLAMA_PORT="$2"
fi

OLLAMA_API_BASE="http://${OLLAMA_HOST}:${OLLAMA_PORT}/api"

echo "Using Ollama server: ${OLLAMA_HOST}:${OLLAMA_PORT}"

# Check if Ollama is running
echo "Checking Ollama connection..."
if ! curl -s --connect-timeout 5 "${OLLAMA_API_BASE}/tags" > /dev/null; then
    echo "❌ Cannot connect to Ollama at ${OLLAMA_HOST}:${OLLAMA_PORT}"
    echo "   Please ensure Ollama is running and accessible."
    echo "   For remote servers, make sure Ollama is bound to 0.0.0.0:"
    echo "   OLLAMA_HOST=0.0.0.0 ollama serve"
    exit 1
fi

# Get available models
echo "Checking available models..."
AVAILABLE_MODELS=$(curl -s "${OLLAMA_API_BASE}/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$AVAILABLE_MODELS" ]; then
    echo "❌ Could not retrieve model list from Ollama server"
    exit 1
fi

echo "Available models:"
echo "$AVAILABLE_MODELS" | sed 's/^/  - /'

# Check for suitable models
RECOMMENDED_MODELS="llama3.2:3b llama3.1:8b llama3.2:1b mistral:7b qwen2.5:3b phi3:3.8b"
FOUND_MODEL=""

for model in $RECOMMENDED_MODELS; do
    if echo "$AVAILABLE_MODELS" | grep -q "^${model}$"; then
        FOUND_MODEL="$model"
        break
    fi
done

if [ -z "$FOUND_MODEL" ]; then
    echo "⚠️  No recommended models found. You may need to pull one:"
    echo "   Available options: llama3.2:3b, llama3.1:8b, mistral:7b"
    echo "   Example: ollama pull llama3.2:3b"
    echo "   (On remote server: ssh user@${OLLAMA_HOST} 'ollama pull llama3.2:3b')"
    echo
    echo "Using first available model: $(echo "$AVAILABLE_MODELS" | head -1)"
    FOUND_MODEL=$(echo "$AVAILABLE_MODELS" | head -1)
fi

echo "✓ Ollama is ready with model: $FOUND_MODEL"

# Create analysis directories
VOICE_MEMOS_DIR="/mnt/voice_memos"
mkdir -p "$VOICE_MEMOS_DIR/analysis"/{projects,tasks,personal,writing,daily_summaries}
mkdir -p "$VOICE_MEMOS_DIR/writing_projects"

echo "✓ Created directory structure"

# Update scripts with Ollama server info
if [ -f "process_memos.py" ]; then
    # Update OLLAMA_API_BASE in the Python script
    sed -i "s|OLLAMA_API_BASE = \"http://localhost:11434/api\"|OLLAMA_API_BASE = \"${OLLAMA_API_BASE}\"|" process_memos.py
    # Update default model if we found a good one
    sed -i "s|MODEL_NAME = \"llama3.2:3b\"|MODEL_NAME = \"${FOUND_MODEL}\"|" process_memos.py
    echo "✓ Updated process_memos.py"
fi

if [ -f "writing_assistant.py" ]; then
    sed -i "s|OLLAMA_API_BASE = \"http://localhost:11434/api\"|OLLAMA_API_BASE = \"${OLLAMA_API_BASE}\"|" writing_assistant.py
    sed -i "s|MODEL_NAME = \"llama3.2:3b\"|MODEL_NAME = \"${FOUND_MODEL}\"|" writing_assistant.py
    echo "✓ Updated writing_assistant.py"
fi

# Make scripts executable
chmod +x process_memos.py writing_assistant.py 2>/dev/null || true

echo "✅ Setup complete!"
echo
echo "Ollama server: ${OLLAMA_HOST}:${OLLAMA_PORT}"
echo "Using model: ${FOUND_MODEL}"
echo
echo "Usage examples:"
echo "  # Process all new memos:"
echo "  python3 process_memos.py --all"
echo
echo "  # Process a specific memo:"
echo "  python3 process_memos.py --memo memo_0046"
echo
echo "  # Use a different model:"
echo "  python3 process_memos.py --all --model mistral:7b"
echo
echo "  # Create daily summary:"
echo "  python3 process_memos.py --daily-summary $(date +%Y%m%d)"
echo
echo "  # List writing ideas:"
echo "  python3 writing_assistant.py --list-ideas"
echo
echo "  # Develop writing from a memo:"
echo "  python3 writing_assistant.py --develop memo_0046"
echo
echo "Directory structure:"
echo "  /mnt/voice_memos/"
echo "  ├── memo_*.{txt,json,srt}     # Your transcripts"
echo "  ├── analysis/"
echo "  │   ├── projects/             # Project-related extractions"
echo "  │   ├── tasks/                # To-dos and reminders"  
echo "  │   ├── personal/             # Mood, sleep, needs"
echo "  │   ├── writing/              # Writing ideas and content"
echo "  │   └── daily_summaries/      # Daily aggregations"
echo "  └── writing_projects/         # Developed writing content"
