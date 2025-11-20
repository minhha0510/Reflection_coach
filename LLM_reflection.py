from ingestion_pipeline import IngestionPipeline
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import requests
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from graph_manager import GraphManager # Assuming GraphManager is in graph_manager.py

# --- CONFIGURATION ---
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") #in the .evn file, it will be invisible when looking at the folder.
#The api_key value and its key need to be entered without ""
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# --- PROMPTS ---

DAILY_GUIDANCE_PROMPT = """
You are a highly skilled performance coach and psychoanalyst specializing in Kolb's Learning Cycle.
Your goal is to guide the user through a reflective process.
Current Step in Cycle: {current_step}

RELEVANT CONTEXT FROM PAST REFLECTIONS:
{graph_context}

You will receive:
1. A user's thought.
2. A JSON template of Kolb's Learning Cycle.

Your task:
1. Map the user's thought to the Kolb's template.
2. Ask 1-2 concise, guiding questions to move them to the *next* step.
3. Be conversational, empathetic, and curious.
"""

DAILY_SUMMARY_PROMPT = """
Analyze the *entire* conversation. Output ONLY a JSON object with this schema:
{
  "summary": "Concise one-sentence summary.",
  "trigger_cues": "Physical or environmental trigger.",
  "emotional_response": "Primary feeling before action.",
  "cognitive_pattern": "Core thought process or story.",
  "behavioral_action": "Action taken.",
  "proposed_solution": "Final proposed experiment/solution.",
  "key_takeaway": "Main lesson learned."
}
"""

WEEKLY_SYSTEM_PROMPT = """
You are a performance coach. The user is reviewing their week.
CONTEXT FROM LAST WEEK'S SUMMARY: 
{prev_context}

CURRENT WEEK'S DATA:
{current_data}

Goal: Help the user identify themes and connect them to last week's progress. 
Ask exactly two insightful, connected questions at a time.
"""

WEEKLY_SUMMARY_PROMPT = """
Based on the user's reflections this week and our conversation, generate a JSON summary to serve as the starting point for NEXT week.
Output ONLY JSON:
{
    "week_theme": "The main theme of this week",
    "major_wins": "What went well",
    "struggles": "Recurring blockers",
    "focus_for_next_week": "What specifically should we focus on next week?"
}
"""

# --- CLASS DEFINITION ---

class ReflectionCoach:
    def __init__(self):
        # Setup Paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.daily_dir = os.path.join(self.script_dir, "daily")
        self.weekly_dir = os.path.join(self.script_dir, "weekly")
        self.context_file = os.path.join(self.weekly_dir, "context_memory.json")
        
        # Ensure directories exist
        os.makedirs(self.daily_dir, exist_ok=True)
        os.makedirs(self.weekly_dir, exist_ok=True)

        # Initialize Graph Components
        self.graph_manager = GraphManager(os.path.join(self.script_dir, "reflection_graph.json"))
        self.ingestion_pipeline = IngestionPipeline(self.graph_manager)

        # Key Bindings for Multi-line Input
        self.kb = KeyBindings()

        @self.kb.add('escape', 'enter') 
        def _(event):
            """Submit input when Esc then Enter is pressed."""
            event.app.exit(event.app.current_buffer.text)

    def _get_multiline_input(self, label="You"):
        """
        Uses prompt_toolkit to allow multi-line input.
        User presses Esc, then Enter to submit.
        """
        print(f"\n--- {label} (Type away! Press 'Esc' then 'Enter' to send) ---")
        style = HTML(f'<style fg="#ansigreen">{label}: </style>')
        
        user_text = prompt(
            style, 
            multiline=True, 
            key_bindings=self.kb,
            bottom_toolbar=HTML(" <b>[Esc] + [Enter]</b> to submit | <b>Type 'DONE' or 'SAVE'</b> (alone on line) to finish.")
        )
        return user_text.strip()

    def _strip_markdown_json(self, text):
        """Strip markdown code blocks from JSON responses"""
        import re
        # Remove ```json ... ``` or ``` ... ``` blocks
        text = text.strip()
        if text.startswith('```'):
            # Find the first newline after opening ```
            first_newline = text.find('\n')
            # Find the closing ```
            last_backticks = text.rfind('```')
            if first_newline != -1 and last_backticks != -1:
                text = text[first_newline+1:last_backticks].strip()
        return text
    
    def _call_llm(self, system_prompt, user_prompt, history=None):
        """Standardized LLM Call"""
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "NA_For_now":
            print("Error: DEEPSEEK_API_KEY not set.")
            return "Error: API_KEY not set."

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": "deepseek-chat", 
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = requests.post(DEEPSEEK_API_URL, headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"LLM Error: {e}")
            return "Error: LLM failed."

    def load_kolb_template(self):
        path = os.path.join(self.script_dir, 'Kolb_template.json')
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
        return {}

    def save_daily_entry(self, data, raw_conversation):
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        filename = os.path.join(self.daily_dir, f"{timestamp}.md")
        
        content = f"""---
date: {datetime.now().isoformat()}
summary: {data.get('summary')}
solution: {data.get('proposed_solution')}
key_takeaway: {data.get('key_takeaway')}
---
# Full Conversation
{raw_conversation}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved to {filename}")

    def save_weekly_context(self, summary_json):
        """Saves the high-level summary to be used next week."""
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(summary_json, f, indent=2)
        print("Weekly progression context updated.")

    def load_last_week_context(self):
        if os.path.exists(self.context_file):
            with open(self.context_file, 'r') as f:
                return json.load(f)
        return "No previous weekly context found."

    def load_weekly_entries(self):
        # (Same logic as before, simplified)
        seven_days_ago = datetime.now() - timedelta(days=7)
        entries = []
        for fname in sorted(os.listdir(self.daily_dir)):
            if fname.endswith(".md"):
                # Basic check if file is recent enough
                filepath = os.path.join(self.daily_dir, fname)
                if datetime.fromtimestamp(os.path.getmtime(filepath)) > seven_days_ago:
                    with open(filepath, 'r') as f: entries.append(f"--- {fname} ---\n{f.read()}")
        return "\n".join(entries) if entries else "No entries this week."

    # --- MODES ---

    def run_daily_reflection(self):
        print("\n=== DAILY REFLECTION (Kolb Cycle) ===")
        kolb_template = self.load_kolb_template()
        
        # Initial input
        initial_thought = self._get_multiline_input("What's on your mind?")
        if not initial_thought: return

        history = []
        user_input = initial_thought
        
        print("\nStarting Coach Session (Type 'SAVE' on a new line to finish)...")

        while True:
            # 1. Retrieve Context (Ego Walk)
            anchors = self.graph_manager.find_nodes_by_text(user_input)
            anchor_ids = [n['id'] for n in anchors]
            # Limit anchors to top 3 to avoid noise if many matches
            graph_context = self.graph_manager.ego_walk(anchor_ids[:3]) if anchor_ids else "No specific past context found."
            
            # 2. Dynamic Prompting
            prompt_text = DAILY_GUIDANCE_PROMPT.format(
                current_step="General Analysis",
                graph_context=graph_context
            )
            
            # 3. LLM Response
            ai_msg = self._call_llm(prompt_text, user_input, history)
            print(f"\nCoach: {ai_msg}")

            # Add to history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ai_msg})

            # Get Next Input

    def run_weekly_review(self):
        print("\n=== WEEKLY REVIEW & PROGRESSION ===")
        
        # 1. Load Data
        past_context = self.load_last_week_context()
        current_data = self.load_weekly_entries()
        
        if "No entries" in current_data:
            print("Not enough daily entries for a review.")
            return

        print(f"\nContext from previous week: {past_context}")
        
        # 2. Chat Loop
        history = []
        user_input = "I'm ready to review my week."
        
        while True:
            # Inject context into system prompt
            sys_prompt = WEEKLY_SYSTEM_PROMPT.format(
                prev_context=json.dumps(past_context), 
                current_data=current_data[:2000] # Truncate if too large
            )
            
            ai_msg = self._call_llm(sys_prompt, user_input, history)
            print(f"\nCoach: {ai_msg}")
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ai_msg})
            
            user_input = self._get_multiline_input("You")
            
            if user_input.strip().upper() in ['SAVE', 'DONE', 'EXIT']:
                break
        
        # 3. Generate Progression Summary
        print("\nCreating building blocks for next week...")
        full_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        
        summary_raw = self._call_llm(WEEKLY_SUMMARY_PROMPT, full_text)
        try:
            summary_json = json.loads(summary_raw)
            self.save_weekly_context(summary_json)
            print(f"\nNext Week's Focus: {summary_json.get('focus_for_next_week')}")
        except:
            print("Could not generate structured weekly summary.")

# --- MAIN ---

if __name__ == "__main__":
    agent = ReflectionCoach()
    
    while True:
        print("\n1: Daily Reflection")
        print("2: Weekly Review")
        print("3: Exit")
        choice = input("Select: ")
        
        if choice == '1': agent.run_daily_reflection()
        elif choice == '2': agent.run_weekly_review()
        elif choice == '3': break