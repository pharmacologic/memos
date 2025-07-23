# Voice Memo Analysis Pipeline

A comprehensive system for transcribing, analyzing, and developing ideas from voice memos using AI. This pipeline combines whisper.cpp for transcription with local LLMs (via Ollama) for intelligent content extraction and writing assistance.

## Features

### 🎤 Audio Transcription
- **Bulk transcription** with whisper.cpp and duplicate detection
- **Multiple audio formats** supported (MP3, WAV, FLAC)
- **Smart datetime extraction** from spoken content for automatic file naming
- **OpenVINO acceleration** support for faster processing
- **VAD (Voice Activity Detection)** for improved transcription quality

### 🧠 AI-Powered Analysis
- **Project extraction**: Identifies project ideas, updates, and planning
- **Task management**: Extracts actionable items, reminders, and deadlines
- **Personal insights**: Analyzes mood, sleep quality, stress indicators
- **Writing ideas**: Captures creative content, rough drafts, and notable phrases
- **Daily summaries**: Aggregates insights across multiple memos

### ✍️ Writing Development
- **Interactive interviews**: AI-powered coaching sessions for developing ideas
- **Context-aware conversations**: Builds on related memos and extracted insights
- **Draft creation**: Develops voice memo content into structured writing
- **Session management**: Saves and resumes writing development sessions

### 🔄 Workflow Automation
- **USB auto-sync**: Automatic mounting and syncing of voice recorder drives
- **Batch processing**: Handle hundreds of audio files efficiently
- **Flexible configuration**: Support for local or remote Ollama servers

## Requirements

### System Dependencies
- **Python 3.8+** with `requests` library
- **whisper.cpp** compiled with CLI support
- **Ollama** server (local or remote)
- **curl** and **jq** for API interactions
- **rsync** (for USB sync functionality)

### Hardware Recommendations
- **CPU**: Multi-core processor (Intel/AMD)
- **RAM**: 8GB+ (16GB+ recommended for larger models)
- **GPU**: Optional but recommended for OpenVINO acceleration
- **Storage**: Fast SSD for audio file processing

### Ollama Models
Compatible with various models. Recommended options:
- `llama3.2:3b` (default, balanced performance)
- `llama3.1:8b` (higher quality analysis)
- `mistral:7b` (alternative option)
- `qwen2.5:3b` or `phi3:3.8b` (lighter alternatives)

## Quick Start

### 1. Install Dependencies

#### Install whisper.cpp
```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
# Download a model
./models/download-ggml-model.sh large-v3-turbo
```

#### Install and start Ollama
```bash
# Install Ollama (see https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2:3b

# Start server
ollama serve
```

#### Install Python dependencies
```bash
pip3 install requests
```

### 2. Configure the System
```bash
# Clone this repository
git clone https://github.com/pharmacologic/memos
cd memos

# Run setup script (configures Ollama connection and creates directories)
./setup.sh

# Or specify remote Ollama server
./setup.sh 192.168.1.100 11434
```

### 3. Basic Usage

#### Transcribe Audio Files
```bash
# Configure transcription settings in bulk_transcribe.sh
# Edit WHISPER_DIR, INPUT_DIR, and OUTPUT_DIR variables

# Run bulk transcription
./bulk_transcribe.sh
```

#### Analyze Transcripts
```bash
# Process all new memos
python3 process_memos.py --all

# Process specific memo
python3 process_memos.py --memo memo_0046

# Create daily summary
python3 process_memos.py --daily-summary 20250723
```

#### Develop Writing Ideas
```bash
# List all writing ideas
python3 writing_assistant.py --list-ideas

# Develop writing from a memo
python3 writing_assistant.py --develop memo_0046

# Interactive AI-powered interview
python3 writing_assistant.py --interactive memo_0046
```

## Configuration

### Transcription Settings (`bulk_transcribe.sh`)

```bash
# Core paths
WHISPER_DIR="$HOME/software/whisper.cpp"
MODEL_PATH="models/ggml-large-v3-turbo.bin"
INPUT_DIR="/mnt/voice_recorder"
OUTPUT_DIR="/mnt/voice_memos"

# Optional enhancements
VAD_MODEL_PATH="models/ggml-silero-v5.1.2.bin"  # Voice activity detection
OPENVINO_SETUP="/opt/openvino/runtime/setupvars.sh"  # Hardware acceleration
OPENVINO_DEVICE="GPU"  # CPU, GPU, NPU, or AUTO

# LLM integration for datetime extraction
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2:3b"
```

### Analysis Settings

The setup script automatically configures `process_memos.py` and `writing_assistant.py` with your Ollama server settings. Manual configuration:

```python
# In process_memos.py and writing_assistant.py
OLLAMA_API_BASE = "http://localhost:11434/api"
MODEL_NAME = "llama3.2:3b"
```

### USB Auto-Sync (Optional)

For automatic syncing of voice recorder files:

```bash
# Edit USB UUID in usb_auto_sync.sh
USB_UUID="YOUR_USB_UUID_HERE"

# Run setup (requires root)
sudo ./usb_auto_sync.sh
```

## Directory Structure

```
/mnt/voice_memos/
├── memo_*.{txt,json,srt}           # Transcribed voice memos
├── analysis/
│   ├── projects/                   # Project-related extractions
│   ├── tasks/                      # Action items and reminders
│   ├── personal/                   # Mood, sleep, stress analysis
│   ├── writing/                    # Writing ideas and content
│   └── daily_summaries/            # Daily aggregated insights
└── writing_projects/               # Developed writing content
    ├── memo_*_developed.md         # Extended writing pieces
    ├── memo_*_interview_*.json     # Interview session logs
    └── memo_*_insights_*.md        # AI-generated insights
```

## Usage Examples

### Common Workflows

#### 1. Daily Voice Memo Processing
```bash
# Morning: Sync from voice recorder (if using USB auto-sync)
# USB device plugged in → automatic sync

# Transcribe new recordings
./bulk_transcribe.sh

# Analyze all new content
python3 process_memos.py --all

# Review today's insights
python3 process_memos.py --daily-summary $(date +%Y%m%d)
```

#### 2. Writing Development Session
```bash
# Find interesting writing ideas
python3 writing_assistant.py --list-ideas

# Start interactive development
python3 writing_assistant.py --interactive memo_0046

# Resume previous session
python3 writing_assistant.py --resume /mnt/voice_memos/writing_projects/memo_0046_interactive_interview_20250723_1234.json
```

#### 3. Project Planning Review
```bash
# Extract project updates from recent memos
python3 process_memos.py --memo memo_0095 --memo memo_0096

# Review extracted projects
cat /mnt/voice_memos/analysis/projects/memo_*_projects.json
```

### Advanced Options

#### Custom Model Usage
```bash
# Use different model for analysis
python3 process_memos.py --all --model mistral:7b

# Use specific model for writing
python3 writing_assistant.py --develop memo_0046 --model llama3.1:8b
```

#### Remote Ollama Server
```bash
# Configure for remote server
./setup.sh 192.168.1.100 11434

# Or set environment variables
export OLLAMA_HOST=192.168.1.100
export OLLAMA_PORT=11434
./setup.sh
```

## Interactive Writing Features

The enhanced interactive interview mode (`--interactive`) provides:

### Context Loading
- Loads original transcript and all analysis results
- Finds related memos using text similarity
- Builds rich context from projects, tasks, and personal insights

### AI-Powered Conversations
- Dynamic opening questions based on memo content
- Follow-up questions that build on responses
- Context-aware prompts referencing related content
- Meta-commands: `summary`, `context`, `quit`

### Session Management
- Full conversation history with timestamps
- Detailed session logs with metadata
- AI-generated insights and next steps
- Resume interrupted conversations with full context

## Troubleshooting

### Common Issues

#### Ollama Connection Errors
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# For remote servers, ensure binding to 0.0.0.0
OLLAMA_HOST=0.0.0.0 ollama serve
```

#### Transcription Issues
```bash
# Verify whisper-cli exists and is executable
ls -la ~/software/whisper.cpp/build/bin/whisper-cli

# Check model file
ls -la ~/software/whisper.cpp/models/ggml-large-v3-turbo.bin

# Test with single file
cd ~/software/whisper.cpp
./build/bin/whisper-cli -m models/ggml-large-v3-turbo.bin -f /path/to/audio.mp3
```

#### Permission Issues
```bash
# Ensure output directory is writable
sudo chown -R $USER:$USER /mnt/voice_memos
```

#### Large File Processing
```bash
# For timeout issues with long transcripts
# Edit bulk_transcribe.sh and increase timeout values
# Or process files individually
```

### Performance Optimization

#### For Large Batches
- Enable VAD for better transcription quality
- Use OpenVINO for GPU acceleration
- Process during off-peak hours
- Monitor disk space in output directory

#### For Better Analysis
- Use larger models (llama3.1:8b) for higher quality
- Adjust temperature settings for more creative/conservative analysis
- Regular cleanup of old analysis files

## Contributing

### Development Setup
1. Read `CLAUDE.md` for development guidelines
2. Follow existing code patterns and conventions
3. Test changes with small batches first
4. Update documentation for new features

### Adding New Analysis Types
1. Add new category to `ANALYSIS_DIRS` in `process_memos.py`
2. Create corresponding analysis prompt
3. Update directory creation in `setup.sh`
4. Add usage examples to documentation

## License

[GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Acknowledgments

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) for efficient speech-to-text
- [Ollama](https://ollama.ai) for local LLM inference
- [OpenVINO](https://github.com/openvinotoolkit/openvino) for hardware acceleration
