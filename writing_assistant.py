#!/usr/bin/env python3
"""
Writing Assistant for Voice Memo Analysis
Helps develop writing ideas from voice memo transcripts
"""

import json
import requests
from pathlib import Path
from datetime import datetime
import argparse

OLLAMA_API_BASE = "http://localhost:11434/api"
MODEL_NAME = "llama3.2:3b"
VOICE_MEMOS_DIR = Path("/mnt/voice_memos")
ANALYSIS_DIR = VOICE_MEMOS_DIR / "analysis"
WRITING_DIR = VOICE_MEMOS_DIR / "writing_projects"

def ensure_writing_dir():
    """Create writing projects directory"""
    WRITING_DIR.mkdir(exist_ok=True)

def call_ollama(prompt, model=MODEL_NAME):
    """Call Ollama API"""
    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,  # Higher creativity for writing
                    "top_p": 0.9
                }
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
        return None

def list_writing_ideas():
    """List all writing ideas from analysis files"""
    writing_files = list((ANALYSIS_DIR / "writing").glob("*_writing.json"))
    
    all_ideas = []
    for file_path in sorted(writing_files):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                memo_id = data.get('memo_id', file_path.stem.split('_')[0])
                
                if data.get('writing_ideas'):
                    for idea in data['writing_ideas']:
                        all_ideas.append({
                            'memo_id': memo_id,
                            'idea': idea,
                            'timestamp': data.get('timestamp', '')
                        })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    if not all_ideas:
        print("No writing ideas found. Run the main processor first.")
        return
    
    print(f"\nFound {len(all_ideas)} writing ideas:\n")
    for i, item in enumerate(all_ideas, 1):
        print(f"{i:2d}. [{item['memo_id']}] {item['idea'][:100]}...")
    
    return all_ideas

def develop_writing_idea(memo_id, original_transcript=None):
    """Develop a specific writing idea with follow-up questions"""
    
    # Get the original transcript
    if not original_transcript:
        transcript_file = VOICE_MEMOS_DIR / f"{memo_id}.txt"
        try:
            with open(transcript_file, 'r') as f:
                original_transcript = f.read()
        except FileNotFoundError:
            print(f"Transcript file not found: {transcript_file}")
            return
    
    # Get the writing analysis
    writing_file = (ANALYSIS_DIR / "writing") / f"{memo_id}_writing.json"
    try:
        with open(writing_file, 'r') as f:
            writing_data = json.load(f)
    except FileNotFoundError:
        print(f"Writing analysis not found for {memo_id}")
        return
    
    print(f"\nDeveloping writing ideas from {memo_id}...\n")
    
    # Create development prompt
    prompt = f"""You are helping a writer develop ideas from their voice memo. 

Original transcript:
{original_transcript}

Extracted writing elements:
- Ideas: {writing_data.get('writing_ideas', [])}
- Rough drafts: {writing_data.get('rough_drafts', [])}
- Notable phrases: {writing_data.get('quotes_phrases', [])}

Please help develop these ideas by:

1. EXPANDED CONCEPTS: Take the writing ideas and expand them into more detailed concepts
2. STORY POSSIBILITIES: Suggest specific stories, articles, or pieces that could emerge
3. RESEARCH DIRECTIONS: What research or additional thinking would help develop these ideas?
4. NEXT STEPS: Concrete actions the writer could take to move these ideas forward
5. CONNECTING THEMES: How do these ideas connect to broader themes in the writer's work?

Be specific and actionable. Focus on turning voice memo fragments into developed writing projects.

Response:"""
    
    response = call_ollama(prompt)
    if response:
        # Save the development
        output_file = WRITING_DIR / f"{memo_id}_development.md"
        with open(output_file, 'w') as f:
            f.write(f"# Writing Development for {memo_id}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## Original Ideas\n\n")
            for idea in writing_data.get('writing_ideas', []):
                f.write(f"- {idea}\n")
            f.write(f"\n## Development\n\n{response}\n")
        
        print(f"Development saved to: {output_file}")
        print(f"\n{response}")
    else:
        print("Failed to generate development")

def create_writing_draft(memo_ids):
    """Create a rough draft from multiple related memos"""
    if isinstance(memo_ids, str):
        memo_ids = [memo_ids]
    
    # Collect transcripts and analyses
    all_content = []
    for memo_id in memo_ids:
        transcript_file = VOICE_MEMOS_DIR / f"{memo_id}.txt"
        writing_file = (ANALYSIS_DIR / "writing") / f"{memo_id}_writing.json"
        
        try:
            with open(transcript_file, 'r') as f:
                transcript = f.read()
            with open(writing_file, 'r') as f:
                writing_data = json.load(f)
            
            all_content.append({
                'memo_id': memo_id,
                'transcript': transcript,
                'writing_data': writing_data
            })
        except FileNotFoundError as e:
            print(f"Warning: Could not find files for {memo_id}: {e}")
    
    if not all_content:
        print("No content found for draft creation")
        return
    
    # Create draft prompt
    content_summary = ""
    for item in all_content:
        content_summary += f"\nMemo {item['memo_id']}:\n"
        content_summary += f"Transcript: {item['transcript'][:300]}...\n"
        content_summary += f"Ideas: {item['writing_data'].get('writing_ideas', [])}\n"
    
    prompt = f"""You are helping a writer create a rough draft from their voice memo content.

Source material:
{content_summary}

Please create a coherent rough draft that:
1. Identifies the main theme or story emerging from this content
2. Structures the ideas into a logical flow
3. Develops the most promising concepts
4. Maintains the authentic voice from the original memos
5. Suggests areas that need more development

This should be a working draft that the writer can build upon, not a polished piece.

Draft:"""
    
    response = call_ollama(prompt)
    if response:
        # Save draft
        draft_name = f"draft_{'_'.join(memo_ids)}_{datetime.now().strftime('%Y%m%d')}"
        output_file = WRITING_DIR / f"{draft_name}.md"
        
        with open(output_file, 'w') as f:
            f.write(f"# Draft from Memos: {', '.join(memo_ids)}\n\n")
            f.write(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Source memos:** {', '.join(memo_ids)}\n\n")
            f.write(response)
        
        print(f"Draft saved to: {output_file}")
        print(f"\n{response}")
    else:
        print("Failed to generate draft")

def interview_mode(memo_id):
    """Interactive interview about a memo's content"""
    # Load memo and analysis
    transcript_file = VOICE_MEMOS_DIR / f"{memo_id}.txt"
    writing_file = (ANALYSIS_DIR / "writing") / f"{memo_id}_writing.json"
    
    try:
        with open(transcript_file, 'r') as f:
            transcript = f.read()
        with open(writing_file, 'r') as f:
            writing_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Files not found for {memo_id}: {e}")
        return
    
    print(f"\n=== Interview Mode for {memo_id} ===")
    print("I'll ask you questions to help develop the ideas in this memo.")
    print("Type 'quit' to exit, 'next' for the next question.\n")
    
    # Get interview questions from the analysis
    questions = writing_data.get('interview_questions', [])
    if not questions:
        print("No interview questions found in analysis.")
        return
    
    interview_log = []
    
    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}: {question}")
        response = input("> ")
        
        if response.lower() == 'quit':
            break
        elif response.lower() == 'next':
            continue
        else:
            interview_log.append({
                'question': question,
                'response': response
            })
    
    # Save interview
    if interview_log:
        output_file = WRITING_DIR / f"{memo_id}_interview_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'memo_id': memo_id,
                'timestamp': datetime.now().isoformat(),
                'interview': interview_log
            }, f, indent=2)
        
        print(f"\nInterview saved to: {output_file}")

def main():
    global MODEL_NAME
    
    parser = argparse.ArgumentParser(description="Writing assistant for voice memos")
    parser.add_argument("--list-ideas", action="store_true", help="List all writing ideas")
    parser.add_argument("--develop", help="Develop ideas from specific memo")
    parser.add_argument("--draft", nargs="+", help="Create draft from memo(s)")
    parser.add_argument("--interview", help="Interactive interview about a memo")
    parser.add_argument("--model", default=MODEL_NAME, help="Ollama model to use")
    
    args = parser.parse_args()
    
    MODEL_NAME = args.model
    
    ensure_writing_dir()
    
    if args.list_ideas:
        list_writing_ideas()
    elif args.develop:
        develop_writing_idea(args.develop)
    elif args.draft:
        create_writing_draft(args.draft)
    elif args.interview:
        interview_mode(args.interview)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
