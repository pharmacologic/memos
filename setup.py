#!/bin/bash
# Setup script for voice memo analysis

set -e

echo "Setting up voice memo analysis pipeline..."

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama is not running. Please start Ollama first."
    echo "   ollama serve"
    exit 1
fi

# Check if we have a suitable model
if ! ollama list | grep -q "llama3.2:3b\|llama3.1:8b\|mistral"; then
    echo "📥 Pulling a suitable model (llama3.2:3b)..."
    ollama pull llama3.2:3b
fi

echo "✓ Ollama is ready"

# Create analysis directories
VOICE_MEMOS_DIR="/mnt/voice_memos"
mkdir -p "$VOICE_MEMOS_DIR/analysis"/{projects,tasks,personal,writing,daily_summaries}
mkdir -p "$VOICE_MEMOS_DIR/writing_projects"

echo "✓ Created directory structure"

# Make scripts executable
chmod +x process_memos.py writing_assistant.py

echo "✅ Setup complete!"
echo
echo "Usage examples:"
echo "  # Process all new memos:"
echo "  python3 process_memos.py --all"
echo
echo "  # Process a specific memo:"
echo "  python3 process_memos.py --memo memo_0046"
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
