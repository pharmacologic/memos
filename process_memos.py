#!/usr/bin/env python3
"""
Voice Memo Analysis Pipeline
Processes transcribed voice memos through multiple focused LLM analyses
"""

import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime
import argparse

# Configuration
OLLAMA_API_BASE = "http://localhost:11434/api"
MODEL_NAME = "llama3.2:3b"  # Adjust to your preferred model
VOICE_MEMOS_DIR = Path("/mnt/voice_memos")
OUTPUT_DIR = VOICE_MEMOS_DIR / "analysis"

# Create analysis subdirectories
ANALYSIS_DIRS = {
    'projects': OUTPUT_DIR / "projects",
    'tasks': OUTPUT_DIR / "tasks", 
    'personal': OUTPUT_DIR / "personal",
    'writing': OUTPUT_DIR / "writing",
    'daily': OUTPUT_DIR / "daily_summaries"
}

def ensure_directories():
    """Create analysis directory structure"""
    for dir_path in ANALYSIS_DIRS.values():
        dir_path.mkdir(parents=True, exist_ok=True)

def call_ollama(prompt, model=MODEL_NAME):
    """Call Ollama API with error handling"""
    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
        return None

def extract_projects(text, memo_id):
    """Extract project outlines and ideas"""
    prompt = f"""Analyze this voice memo transcript for project-related content. Extract:

1. PROJECT IDEAS: New project concepts mentioned
2. PROJECT UPDATES: Progress on existing projects
3. PROJECT PLANNING: Steps, timelines, or resource needs mentioned

Format as JSON with keys: project_ideas, project_updates, project_planning
Only include items that are clearly project-related. If nothing found, return empty arrays.

Transcript:
{text}

JSON Response:"""
    
    response = call_ollama(prompt)
    if response:
        try:
            data = json.loads(response.strip())
            data['memo_id'] = memo_id
            data['timestamp'] = datetime.now().isoformat()
            return data
        except json.JSONDecodeError:
            print(f"Failed to parse projects JSON for {memo_id}")
    return None

def extract_tasks(text, memo_id):
    """Extract actionable tasks and reminders"""
    prompt = f"""Extract actionable items from this voice memo:

1. TODO ITEMS: Specific tasks to complete
2. REMINDERS: Things to remember or follow up on
3. DEADLINES: Time-sensitive items mentioned

Format as JSON with keys: todo_items, reminders, deadlines
Each item should include the text and estimated priority (high/medium/low).
If nothing found, return empty arrays.

Transcript:
{text}

JSON Response:"""
    
    response = call_ollama(prompt)
    if response:
        try:
            data = json.loads(response.strip())
            data['memo_id'] = memo_id
            data['timestamp'] = datetime.now().isoformat()
            return data
        except json.JSONDecodeError:
            print(f"Failed to parse tasks JSON for {memo_id}")
    return None

def extract_personal_insights(text, memo_id):
    """Extract mood, sleep, and personal observations"""
    prompt = f"""Analyze this voice memo for personal insights:

1. MOOD_SENTIMENT: Overall emotional tone (positive/negative/neutral/mixed)
2. SLEEP_QUALITY: Any mentions of sleep, rest, fatigue, energy levels
3. STRESS_INDICATORS: Signs of stress, overwhelm, or anxiety
4. NEEDS_SUPPORT: Areas where financial or other support is mentioned
5. SELF_REFLECTION: Personal insights or self-observations

Format as JSON with these keys. Provide brief quotes from the transcript as evidence.
If nothing found for a category, use null.

Transcript:
{text}

JSON Response:"""
    
    response = call_ollama(prompt)
    if response:
        try:
            data = json.loads(response.strip())
            data['memo_id'] = memo_id
            data['timestamp'] = datetime.now().isoformat()
            return data
        except json.JSONDecodeError:
            print(f"Failed to parse personal JSON for {memo_id}")
    return None

def extract_writing_content(text, memo_id):
    """Extract writing ideas and content"""
    prompt = f"""Analyze this voice memo for writing-related content:

1. WRITING_IDEAS: Story ideas, article topics, creative concepts
2. ROUGH_DRAFTS: Any narrative or structured content that could become writing
3. QUOTES_PHRASES: Interesting turns of phrase, metaphors, or quotable moments
4. INTERVIEW_QUESTIONS: Follow-up questions to explore these ideas further

Format as JSON. For interview_questions, create 2-3 specific questions that would help develop the ideas mentioned.

Transcript:
{text}

JSON Response:"""
    
    response = call_ollama(prompt)
    if response:
        try:
            data = json.loads(response.strip())
            data['memo_id'] = memo_id
            data['timestamp'] = datetime.now().isoformat()
            return data
        except json.JSONDecodeError:
            print(f"Failed to parse writing JSON for {memo_id}")
    return None

def process_memo(memo_path):
    """Process a single memo through all analysis functions"""
    memo_id = memo_path.stem
    print(f"Processing {memo_id}...")
    
    # Read transcript
    try:
        with open(memo_path, 'r') as f:
            text = f.read().strip()
    except Exception as e:
        print(f"Error reading {memo_path}: {e}")
        return
    
    if not text:
        print(f"Empty transcript for {memo_id}")
        return
    
    # Run analyses
    analyses = {
        'projects': extract_projects(text, memo_id),
        'tasks': extract_tasks(text, memo_id),
        'personal': extract_personal_insights(text, memo_id),
        'writing': extract_writing_content(text, memo_id)
    }
    
    # Save results
    for analysis_type, data in analyses.items():
        if data:
            output_file = ANALYSIS_DIRS[analysis_type] / f"{memo_id}_{analysis_type}.json"
            try:
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"  ✓ Saved {analysis_type} analysis")
            except Exception as e:
                print(f"  ✗ Failed to save {analysis_type}: {e}")

def create_daily_summary(date_str=None):
    """Create a summary of all analyses for a given day"""
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")
    
    print(f"Creating daily summary for {date_str}...")
    
    # Collect all analyses from the day
    all_data = {
        'date': date_str,
        'projects': [],
        'tasks': [],
        'personal': [],
        'writing': []
    }
    
    for analysis_type, dir_path in ANALYSIS_DIRS.items():
        if analysis_type == 'daily_summaries':
            continue
            
        for file_path in dir_path.glob(f"*{analysis_type}.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Check if timestamp matches date (rough check)
                    if date_str in data.get('timestamp', ''):
                        all_data[analysis_type].append(data)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    # Save daily summary
    summary_file = ANALYSIS_DIRS['daily'] / f"summary_{date_str}.json"
    with open(summary_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"Daily summary saved to {summary_file}")

def main():
    global MODEL_NAME
    
    parser = argparse.ArgumentParser(description="Process voice memo transcripts")
    parser.add_argument("--memo", help="Process specific memo (e.g., memo_0001)")
    parser.add_argument("--all", action="store_true", help="Process all unprocessed memos")
    parser.add_argument("--daily-summary", help="Create daily summary (YYYYMMDD)")
    parser.add_argument("--model", default=MODEL_NAME, help="Ollama model to use")
    
    args = parser.parse_args()
    
    MODEL_NAME = args.model
    
    ensure_directories()
    
    if args.daily_summary:
        create_daily_summary(args.daily_summary)
    elif args.memo:
        memo_path = VOICE_MEMOS_DIR / f"{args.memo}.txt"
        if memo_path.exists():
            process_memo(memo_path)
        else:
            print(f"Memo not found: {memo_path}")
    elif args.all:
        # Process all .txt files that don't have corresponding analysis
        txt_files = list(VOICE_MEMOS_DIR.glob("memo_*.txt"))
        for txt_file in sorted(txt_files):
            memo_id = txt_file.stem
            # Check if already processed (look for any analysis file)
            if any((ANALYSIS_DIRS[atype] / f"{memo_id}_{atype}.json").exists() 
                   for atype in ['projects', 'tasks', 'personal', 'writing']):
                print(f"Skipping {memo_id} (already processed)")
                continue
            process_memo(txt_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
