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

1. **process_memos.py** - Main analysis pipeline that processes voice memo transcripts through four focused analyses:
   - Projects: Extracts project ideas, updates, and planning
   - Tasks: Identifies actionable items, reminders, and deadlines
   - Personal: Analyzes mood, sleep quality, stress indicators
   - Writing: Extracts writing ideas, rough drafts, and notable phrases

2. **writing_assistant.py** - Writing development tool that helps expand voice memo content into structured writing projects with interview modes and draft creation. Features both legacy static interviews and enhanced AI-powered interactive interviews with context awareness.

3. **setup.sh** - Configuration script that handles Ollama server setup, model detection, and directory structure creation.

### Data Flow

1. Voice memos are transcribed to `/mnt/voice_memos/memo_*.txt`
2. `process_memos.py` analyzes transcripts and saves structured JSON to `/mnt/voice_memos/analysis/`
3. `writing_assistant.py` processes writing analyses to create developed content in `/mnt/voice_memos/writing_projects/`

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

- Python 3 with `requests` library
- Ollama server running locally or on network
- Compatible models: llama3.2:3b, llama3.1:8b, mistral:7b, qwen2.5:3b, phi3:3.8b