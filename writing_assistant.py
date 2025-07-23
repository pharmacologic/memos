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
import re
from collections import defaultdict

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

def load_memo_context(memo_id):
    """Load full context for a memo including transcript and all analyses"""
    context = {
        'memo_id': memo_id,
        'transcript': '',
        'analyses': {}
    }
    
    # Load original transcript
    transcript_file = VOICE_MEMOS_DIR / f"{memo_id}.txt"
    try:
        with open(transcript_file, 'r') as f:
            context['transcript'] = f.read().strip()
    except FileNotFoundError:
        print(f"Warning: Transcript not found for {memo_id}")
        return None
    
    # Load all analyses
    analysis_types = ['writing', 'projects', 'tasks', 'personal']
    for analysis_type in analysis_types:
        analysis_file = (ANALYSIS_DIR / analysis_type) / f"{memo_id}_{analysis_type}.json"
        try:
            with open(analysis_file, 'r') as f:
                context['analyses'][analysis_type] = json.load(f)
        except FileNotFoundError:
            context['analyses'][analysis_type] = {}
    
    return context

def find_related_memos(memo_id, max_related=3):
    """Find related memos using simple text similarity"""
    target_context = load_memo_context(memo_id)
    if not target_context:
        return []
    
    target_text = target_context['transcript'].lower()
    target_words = set(re.findall(r'\b\w{4,}\b', target_text))  # Words 4+ chars
    
    related_scores = []
    
    # Get all memo files
    memo_files = list(VOICE_MEMOS_DIR.glob("memo_*.txt"))
    
    for memo_file in memo_files:
        other_memo_id = memo_file.stem
        if other_memo_id == memo_id:
            continue
            
        try:
            with open(memo_file, 'r') as f:
                other_text = f.read().lower()
            
            other_words = set(re.findall(r'\b\w{4,}\b', other_text))
            
            # Simple Jaccard similarity
            if len(target_words) > 0 and len(other_words) > 0:
                intersection = len(target_words & other_words)
                union = len(target_words | other_words)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.1:  # Minimum threshold
                    related_scores.append({
                        'memo_id': other_memo_id,
                        'similarity': similarity,
                        'context': load_memo_context(other_memo_id)
                    })
        except Exception as e:
            continue
    
    # Sort by similarity and return top results
    related_scores.sort(key=lambda x: x['similarity'], reverse=True)
    return related_scores[:max_related]

def build_interview_context(memo_id):
    """Build rich context for interactive interview"""
    main_context = load_memo_context(memo_id)
    if not main_context:
        return None
    
    related_memos = find_related_memos(memo_id)
    
    context = {
        'main_memo': main_context,
        'related_memos': related_memos,
        'writing_ideas': main_context['analyses'].get('writing', {}).get('WRITING_IDEAS', []),
        'initial_questions': main_context['analyses'].get('writing', {}).get('INTERVIEW_QUESTIONS', []),
        'projects': main_context['analyses'].get('projects', {}),
        'tasks': main_context['analyses'].get('tasks', {}),
        'personal_insights': main_context['analyses'].get('personal', {})
    }
    
    return context

class ConversationState:
    """Manage conversation state and memory"""
    def __init__(self, memo_id, context):
        self.memo_id = memo_id
        self.context = context
        self.conversation_history = []
        self.explored_topics = set()
        self.current_focus = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_exchange(self, question, response, topic=None):
        """Add a question-response exchange to history"""
        exchange = {
            'question': question,
            'response': response,
            'topic': topic,
            'timestamp': datetime.now().isoformat()
        }
        self.conversation_history.append(exchange)
        
        if topic:
            self.explored_topics.add(topic)
    
    def get_conversation_summary(self):
        """Generate a summary of the conversation so far"""
        if not self.conversation_history:
            return "No conversation yet."
        
        summary = f"Conversation about {self.memo_id} ({len(self.conversation_history)} exchanges):\n"
        for i, exchange in enumerate(self.conversation_history[-3:], 1):  # Last 3 exchanges
            summary += f"{i}. Q: {exchange['question'][:100]}...\n"
            summary += f"   A: {exchange['response'][:100]}...\n"
        
        return summary
    
    def save_session(self):
        """Save the conversation session"""
        output_file = WRITING_DIR / f"{self.memo_id}_interactive_interview_{self.session_id}.json"
        session_data = {
            'memo_id': self.memo_id,
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'conversation_history': self.conversation_history,
            'explored_topics': list(self.explored_topics),
            'context_summary': {
                'main_memo': self.memo_id,
                'related_memos': [r['memo_id'] for r in self.context['related_memos']],
                'writing_ideas_count': len(self.context['writing_ideas'])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return output_file

def list_interview_sessions(memo_id=None):
    """List available interview sessions for resuming"""
    pattern = f"{memo_id}_interactive_interview_*.json" if memo_id else "*_interactive_interview_*.json"
    session_files = list(WRITING_DIR.glob(pattern))
    
    if not session_files:
        print("No interview sessions found.")
        return []
    
    sessions = []
    for session_file in sorted(session_files):
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            sessions.append({
                'file': session_file,
                'memo_id': data['memo_id'],
                'session_id': data['session_id'],
                'exchanges': len(data.get('conversation_history', [])),
                'timestamp': data.get('timestamp', '')
            })
        except Exception as e:
            continue
    
    print(f"\nFound {len(sessions)} interview sessions:")
    for i, session in enumerate(sessions, 1):
        print(f"{i}. {session['memo_id']} [{session['session_id']}] - {session['exchanges']} exchanges")
    
    return sessions

def resume_interview_session(session_file):
    """Resume an existing interview session"""
    try:
        with open(session_file, 'r') as f:
            session_data = json.load(f)
    except Exception as e:
        print(f"Error loading session: {e}")
        return
    
    memo_id = session_data['memo_id']
    print(f"\n=== Resuming Interview for {memo_id} ===")
    print(f"Session: {session_data['session_id']}")
    print(f"Previous exchanges: {len(session_data.get('conversation_history', []))}")
    
    # Rebuild context
    context = build_interview_context(memo_id)
    if not context:
        print(f"Could not rebuild context for {memo_id}")
        return
    
    # Restore conversation state
    conversation = ConversationState(memo_id, context)
    conversation.session_id = session_data['session_id']
    conversation.conversation_history = session_data.get('conversation_history', [])
    conversation.explored_topics = set(session_data.get('explored_topics', []))
    
    print(f"\nConversation summary:")
    print(conversation.get_conversation_summary())
    print("\nType 'quit' to end, 'summary' for overview, 'context' for related content\n")
    
    # Generate continuation question
    continue_prompt = f"""You are an AI writing coach resuming an interview conversation.

ORIGINAL MEMO: {context['main_memo']['transcript']}

CONVERSATION HISTORY:
{conversation.get_conversation_summary()}

The conversation was interrupted. Generate a question to resume the discussion that:
1. Acknowledges the previous conversation
2. Builds on what was already discussed
3. Moves the conversation forward productively
4. References specific content from their previous responses

RESUMPTION QUESTION:"""
    
    opening_question = call_ollama(continue_prompt)
    if not opening_question:
        opening_question = "Let's continue our conversation - what would you like to explore further from our previous discussion?"
    
    # Continue conversation loop (same as original)
    while True:
        print(f"\nAI Interviewer: {opening_question}")
        user_response = input("> ").strip()
        
        if user_response.lower() == 'quit':
            break
        elif user_response.lower() == 'summary':
            print(f"\n{conversation.get_conversation_summary()}")
            continue
        elif user_response.lower() == 'context':
            print(f"\nOriginal transcript: {context['main_memo']['transcript'][:300]}...")
            print(f"Related memos: {[r['memo_id'] for r in context['related_memos']]}")
            continue
        elif not user_response:
            continue
        
        conversation.add_exchange(opening_question, user_response)
        
        # Generate follow-up (same prompt logic as original)
        followup_prompt = f"""You are an AI writing coach having a conversation with a writer about their voice memo ideas.

ORIGINAL MEMO TRANSCRIPT:
{context['main_memo']['transcript']}

CONVERSATION SO FAR:
{conversation.get_conversation_summary()}

WRITER'S LATEST RESPONSE:
"{user_response}"

AVAILABLE CONTEXT:
- Writing ideas: {context['writing_ideas']}
- Related memos: {[r['memo_id'] for r in context['related_memos']]}
- Projects mentioned: {context['projects']}

Generate a thoughtful follow-up question that:
1. Builds directly on their latest response
2. Helps them go deeper or explore new angles
3. References specific details from their content when relevant
4. Guides them toward actionable writing directions
5. Is conversational and encouraging

If they seem to have exhausted a topic, pivot to exploring a different writing idea or connect to related content.

FOLLOW-UP QUESTION:"""
        
        opening_question = call_ollama(followup_prompt)
        if not opening_question:
            opening_question = "That's interesting! Can you elaborate on that idea?"
    
    # Save updated session
    saved_file = conversation.save_session()
    print(f"\nUpdated conversation saved to: {saved_file}")

def interactive_interview_mode(memo_id):
    """Enhanced interactive interview using LLM for dynamic conversation"""
    print(f"\n=== Interactive Writing Interview for {memo_id} ===")
    print("Starting an AI-guided conversation to develop your writing ideas...")
    print("Type 'quit' to end, 'summary' to see conversation overview, 'context' to see related content\n")
    
    # Build context
    print("Loading context and related memos...")
    context = build_interview_context(memo_id)
    if not context:
        print(f"Could not load context for {memo_id}")
        return
    
    print(f"Found {len(context['related_memos'])} related memos")
    print(f"Identified {len(context['writing_ideas'])} writing ideas to explore\n")
    
    # Initialize conversation state
    conversation = ConversationState(memo_id, context)
    
    # Generate opening question using LLM
    opening_prompt = f"""You are an AI writing coach conducting an interview to help develop writing ideas from voice memos.

MEMO TRANSCRIPT:
{context['main_memo']['transcript']}

EXTRACTED WRITING IDEAS:
{json.dumps(context['writing_ideas'], indent=2)}

INITIAL SUGGESTED QUESTIONS:
{json.dumps(context['initial_questions'], indent=2)}

RELATED CONTENT:
{chr(10).join([f"- {r['memo_id']}: {r['context']['transcript'][:200]}..." for r in context['related_memos']])}

Generate an engaging opening question that:
1. References specific content from the transcript
2. Builds on the extracted writing ideas
3. Is open-ended and thought-provoking
4. Encourages the writer to expand on their ideas

Keep it conversational and specific to their content. Don't be generic.

OPENING QUESTION:"""
    
    opening_question = call_ollama(opening_prompt)
    if not opening_question:
        opening_question = "Tell me more about the ideas in this memo - what excites you most about developing them?"
    
    # Start conversation loop
    while True:
        print(f"\nAI Interviewer: {opening_question}")
        user_response = input("> ").strip()
        
        if user_response.lower() == 'quit':
            break
        elif user_response.lower() == 'summary':
            print(f"\n{conversation.get_conversation_summary()}")
            continue
        elif user_response.lower() == 'context':
            print(f"\nOriginal transcript: {context['main_memo']['transcript'][:300]}...")
            print(f"Related memos: {[r['memo_id'] for r in context['related_memos']]}")
            continue
        elif not user_response:
            continue
        
        # Add to conversation history
        conversation.add_exchange(opening_question, user_response)
        
        # Generate follow-up question using full context
        followup_prompt = f"""You are an AI writing coach having a conversation with a writer about their voice memo ideas.

ORIGINAL MEMO TRANSCRIPT:
{context['main_memo']['transcript']}

CONVERSATION SO FAR:
{conversation.get_conversation_summary()}

WRITER'S LATEST RESPONSE:
"{user_response}"

AVAILABLE CONTEXT:
- Writing ideas: {context['writing_ideas']}
- Related memos: {[r['memo_id'] for r in context['related_memos']]}
- Projects mentioned: {context['projects']}

Generate a thoughtful follow-up question that:
1. Builds directly on their latest response
2. Helps them go deeper or explore new angles
3. References specific details from their content when relevant
4. Guides them toward actionable writing directions
5. Is conversational and encouraging

If they seem to have exhausted a topic, pivot to exploring a different writing idea or connect to related content.

FOLLOW-UP QUESTION:"""
        
        opening_question = call_ollama(followup_prompt)
        if not opening_question:
            opening_question = "That's interesting! Can you elaborate on that idea?"
    
    # Save conversation
    saved_file = conversation.save_session()
    print(f"\nConversation saved to: {saved_file}")
    
    # Generate final insights
    if len(conversation.conversation_history) > 2:
        print("\nGenerating insights from our conversation...")
        
        insights_prompt = f"""Based on this writing interview conversation, provide insights and next steps for the writer.

ORIGINAL MEMO: {context['main_memo']['transcript']}

FULL CONVERSATION:
{chr(10).join([f"Q: {ex['question'][:200]}...{chr(10)}A: {ex['response'][:200]}..." for ex in conversation.conversation_history])}

Provide:
1. KEY THEMES that emerged from the conversation
2. MOST PROMISING writing directions to pursue
3. SPECIFIC NEXT STEPS for developing these ideas
4. CONNECTIONS to their other memos/projects if relevant

Be specific and actionable based on what they actually said.

INSIGHTS:"""
        
        insights = call_ollama(insights_prompt)
        if insights:
            print(f"\n=== Writing Development Insights ===")
            print(insights)
            
            # Save insights to file
            insights_file = WRITING_DIR / f"{memo_id}_interview_insights_{conversation.session_id}.md"
            with open(insights_file, 'w') as f:
                f.write(f"# Interview Insights for {memo_id}\n\n")
                f.write(f"**Session:** {conversation.session_id}\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write(insights)
            
            print(f"\nInsights saved to: {insights_file}")

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
    parser.add_argument("--interview", help="Interactive interview about a memo (legacy mode)")
    parser.add_argument("--interactive", help="Enhanced AI-powered interactive interview")
    parser.add_argument("--list-sessions", nargs="?", const="", help="List interview sessions (optionally for specific memo)")
    parser.add_argument("--resume", help="Resume interview session by session file path")
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
    elif args.interactive:
        interactive_interview_mode(args.interactive)
    elif args.list_sessions is not None:
        memo_id = args.list_sessions if args.list_sessions else None
        list_interview_sessions(memo_id)
    elif args.resume:
        resume_interview_session(Path(args.resume))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
