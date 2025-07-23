# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a voice memo analysis pipeline that processes transcribed voice memos through multiple LLM analyses using Ollama. The system extracts and categorizes content into projects, tasks, personal insights, and writing ideas.

## Setup and Configuration

Run the setup script to configure the system:
```bash
./setup.sh [OLLAMA_HOST] [OLLAMA_PORT]
```

The setup script:
- Checks Ollama server connectivity
- Detects available models (prefers llama3.2:3b, llama3.1:8b, mistral:7b)
- Creates directory structure in `/mnt/voice_memos/`
- Updates Python scripts with correct Ollama server configuration

## Core Commands

### Transcribe audio files:
```bash
# Bulk transcription (configure paths in script first)
./bulk_transcribe.sh

# Key configuration variables in bulk_transcribe.sh:
# - WHISPER_DIR: Path to whisper.cpp installation
# - INPUT_DIR: Directory containing audio files
# - OUTPUT_DIR: Where to save transcripts (typically /mnt/voice_memos)
# - MODEL_PATH: Whisper model to use
```

### Process voice memos:
```bash
# Process all new memos
python3 process_memos.py --all

# Process specific memo
python3 process_memos.py --memo memo_0046

# Use different model
python3 process_memos.py --all --model mistral:7b

# Create daily summary
python3 process_memos.py --daily-summary $(date +%Y%m%d)
```

### Writing assistance:
```bash
# List all writing ideas
python3 writing_assistant.py --list-ideas

# Develop writing from a memo
python3 writing_assistant.py --develop memo_0046

# Create draft from multiple memos
python3 writing_assistant.py --draft memo_0046 memo_0047

# Interactive interview mode (legacy)
python3 writing_assistant.py --interview memo_0046

# Enhanced AI-powered interactive interview
python3 writing_assistant.py --interactive memo_0046

# List interview sessions
python3 writing_assistant.py --list-sessions
python3 writing_assistant.py --list-sessions memo_0046

# Resume interview session
python3 writing_assistant.py --resume /mnt/voice_memos/writing_projects/memo_0046_interactive_interview_20250723_1234.json
```

## Architecture

### Core Components

1. **bulk_transcribe.sh** - Advanced whisper.cpp-based transcription script with:
   - Batch processing with duplicate detection using file signatures
   - Smart datetime extraction from spoken content for automatic file naming
   - OpenVINO acceleration and VAD (Voice Activity Detection) support
   - LLM-powered timestamp analysis for accurate recording start time estimation
   - Comprehensive logging and error handling

2. **process_memos.py** - Main analysis pipeline that processes voice memo transcripts through four focused analyses:
   - Projects: Extracts project ideas, updates, and planning
   - Tasks: Identifies actionable items, reminders, and deadlines
   - Personal: Analyzes mood, sleep quality, stress indicators
   - Writing: Extracts writing ideas, rough drafts, and notable phrases

3. **writing_assistant.py** - Writing development tool that helps expand voice memo content into structured writing projects with interview modes and draft creation. Features both legacy static interviews and enhanced AI-powered interactive interviews with context awareness.

4. **setup.sh** - Configuration script that handles Ollama server setup, model detection, and directory structure creation.

5. **usb_auto_sync.sh** - USB auto-mounting and syncing system for voice recorders with systemd service integration.

### Data Flow

1. **Audio Collection**: Voice recorder files are synced via USB auto-sync or manual copy to input directory
2. **Transcription**: `bulk_transcribe.sh` processes audio files through whisper.cpp, creating `.txt`, `.json`, and `.srt` files with smart naming
3. **Analysis**: `process_memos.py` analyzes transcripts and saves structured JSON to `/mnt/voice_memos/analysis/`
4. **Writing Development**: `writing_assistant.py` processes writing analyses to create developed content in `/mnt/voice_memos/writing_projects/`

### Directory Structure
```
/mnt/voice_memos/
├── memo_*.{txt,json,srt}     # Source transcripts
├── analysis/
│   ├── projects/             # Project-related extractions
│   ├── tasks/                # To-dos and reminders  
│   ├── personal/             # Mood, sleep, needs
│   ├── writing/              # Writing ideas and content
│   └── daily_summaries/      # Daily aggregations
└── writing_projects/         # Developed writing content
```

## Enhanced Interactive Interview Features

The `--interactive` mode provides AI-powered writing coaching with:

### Context Loading
- Loads full original transcript and all analysis results
- Finds related memos using text similarity (Jaccard similarity with 4+ char words)
- Builds rich context including projects, tasks, and personal insights

### Dynamic Conversation
- AI-generated opening questions based on specific memo content
- Follow-up questions that build on user responses and conversation history
- Context-aware prompts that reference related memos and extracted insights
- Support for meta-commands: `summary`, `context`, `quit`

### Session Management
- Tracks full conversation history with timestamps
- Saves detailed session logs with metadata
- Generates final insights and actionable next steps
- Creates both JSON conversation logs and markdown insight summaries
- Resume interrupted conversations with full context restoration

### File Outputs
- `{memo_id}_interactive_interview_{session_id}.json` - Full conversation log
- `{memo_id}_interview_insights_{session_id}.md` - AI-generated insights and next steps

## Configuration Details

- Default Ollama server: `localhost:11434`
- Default model: `llama3.2:3b` (configurable)
- API timeout: 300 seconds for longer transcripts
- Temperature settings: 0.3 for analysis, 0.7 for creative writing
- Related memo threshold: 0.1 Jaccard similarity minimum

## Dependencies

### Core Requirements
- **whisper.cpp** compiled with CLI support (`whisper-cli` binary)
- **Python 3** with `requests` library
- **Ollama server** running locally or on network
- **curl** and **jq** for API interactions and JSON processing
- **bash** shell for scripts

### Optional Enhancements
- **OpenVINO** for hardware acceleration
- **VAD model** (Silero) for voice activity detection
- **systemd** and **udev** for USB auto-sync functionality
- **rsync** for file synchronization

### Compatible Ollama Models
- llama3.2:3b (default, recommended)
- llama3.1:8b (higher quality)
- mistral:7b (alternative)
- qwen2.5:3b, phi3:3.8b (lightweight options)

## Transcription Features

### Smart Datetime Extraction
The transcription script can automatically extract timestamps from spoken content and use them for intelligent file naming:

- **Pattern matching**: Recognizes phrases like "today is", "the time is", "it's currently"
- **LLM analysis**: Uses Ollama to extract structured datetime from transcript content
- **Recording time estimation**: Calculates actual recording start time by analyzing SRT timestamps
- **Flexible formats**: Supports various datetime formats (full datetime, date-only, time-only)

### Duplicate Detection
- **File signatures**: Uses size + hash samples from beginning/middle/end of files
- **Batch processing**: Maintains cache across multiple runs
- **Efficient comparison**: Avoids re-transcribing identical files

### OpenVINO Integration
- **Hardware acceleration**: Supports CPU, GPU, NPU acceleration
- **Automatic setup**: Sources OpenVINO environment when available
- **Device selection**: Configurable target device (CPU/GPU/NPU/AUTO)