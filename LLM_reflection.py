from src.ingestion_pipeline import IngestionPipeline
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta, date
import requests
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from src.graph_manager import GraphManager
from src.tracking_manager import TrackingManager
from scripts.experiment_manager import ExperimentManager
from src.context_manager import ContextManager
from src.skill_loader import SkillLoader

# --- CONFIGURATION ---
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") #in the .evn file, it will be invisible when looking at the folder.
#The api_key value and its key need to be entered without ""
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# --- PROMPTS ---

DAILY_GUIDANCE_PROMPT = """
You are a reflective coach who helps people process experiences with patience and depth.

Current Stage: {current_step}

{hierarchical_context}

RELEVANT CONTEXT FROM PAST REFLECTIONS:
{graph_context}

{stage_rules}

CORE PRINCIPLES:
1. Ask ONE question at a time. Wait for full response.
2. Encourage depth before moving to abstraction ("Take your time", "Tell me more").
3. If user mentions physical sensations (stomach, chest, tension), OFFER grounding first.
4. Never stack multiple theoretical frameworks in one response.
5. Validate insights before deepening.
6. Be curious and empathetic, not prescriptive.

{experiment_context}
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

RELEVANT PATTERNS FROM PAST REFLECTIONS:
{graph_context}

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
    "key_takeaway": "Main lesson learned.",
    "focus_for_next_week": "What specifically should we focus on next week?"
}
"""

EXPERIMENT_EXTRACTION_PROMPT = """
Analyze the conversation for any experiments or action plans the user committed to trying.
If found, output a JSON object with this schema. If no experiment found, output {"experiment_found": false}.

{
    "experiment_found": true,
    "title": "Short descriptive name (e.g. '4-7-8 breathing + music')",
    "description": "Full details of what the user will try",
    "success_criteria": "How the user will know it worked",
    "habit_area": "General area this relates to (e.g. 'emotional regulation', 'morning routine')"
}
"""
HABIT_DEVELOPMENT_PROMPT = """
You are a performance coach helping someone break down a life goal into actionable habits.

GOAL: {goal_title}
DESCRIPTION: {goal_description}

Your role is to have a collaborative conversation to:
1. Understand their vision deeply
2. Identify what habits a person who achieved this goal would have
3. Break habits into component skills
4. Prioritize which habits to develop first

Be curious, ask clarifying questions, and build on their ideas.
When the user says 'DONE' or 'FINALIZE', output a final summary as JSON array:
```json
[
    {{"title": "Habit name", "description": "What this looks like in practice", "components": ["Skill 1", "Skill 2"]}}
]
```

Start by acknowledging their goal and asking 1-2 questions to understand it better.
"""

# --- VENT & REFRAME PROMPTS ---

VENT_DECODE_PROMPT = """
You are an emotional intelligence coach analyzing frustration to understand underlying needs.

Analyze the following vent text and identify:
1. The UNDERLYING NEED that isn't being met (be specific and descriptive)
2. The CATEGORY of need (examples: clarity, progress, connection, recognition, autonomy, competence, safety, fairness - but use your judgment, don't force into these)
3. TRIGGER patterns - what situations/people/thoughts activated this frustration
4. The CORE UNMET NEED in one phrase

Vent text:
{vent_text}

Respond with ONLY a JSON object:
{{
    "underlying_need": "Detailed description of what the person actually needs",
    "need_category": "Short label for the type of need (your best judgment)",
    "triggers": ["List of trigger patterns identified"],
    "unmet_need_summary": "One phrase capturing the core unmet need",
    "key_phrases": ["Phrases from the vent that reveal the need"],
    "confidence": 0.0-1.0,
    "brief_analysis": "One sentence explaining your interpretation"
}}
"""

VENT_REFRAME_PROMPT = """
You are an emotional intelligence coach. Based on the underlying need analysis and vent, generate ONE constructive reframe question.

Underlying need: {underlying_need}
Need category: {need_category}
Original vent: {vent_text}

Generate a question that:
- Shifts focus from frustration to actionable clarity
- Directly addresses the unmet need
- Can be answered with a specific, concrete action

Respond with ONLY a JSON object:
{{
    "reframe_question": "The constructive question to ask themselves",
    "why_this_helps": "How this addresses the underlying need"
}}
"""

VENT_MICRO_ACTION_PROMPT = """
Based on the reframe question, suggest ONE concrete 5-minute micro-action.

Reframe question: {reframe_question}
Underlying need: {underlying_need}
Need category: {need_category}

The action must be:
- Completable in 5 minutes or less
- Concrete and specific (not vague)
- A genuine step forward that addresses the underlying need

Respond with ONLY a JSON object:
{{
    "micro_action": "Specific action to take right now",
    "time_estimate": "X minutes",
    "expected_outcome": "How this helps meet the underlying need"
}}
"""

# --- CLASS DEFINITION ---

class ReflectionCoach:
    def __init__(self):
        # Setup Paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, "data")
        self.daily_dir = os.path.join(self.data_dir, "conversation_history", "daily")
        self.weekly_dir = os.path.join(self.data_dir, "conversation_history", "weekly")
        self.context_file = os.path.join(self.weekly_dir, "context_memory.json")
        
        # Ensure directories exist
        os.makedirs(self.daily_dir, exist_ok=True)
        os.makedirs(self.weekly_dir, exist_ok=True)

        # Initialize Graph Components
        self.graph_manager = GraphManager(os.path.join(self.data_dir, "reflection_graph.json"))
        self.ingestion_pipeline = IngestionPipeline(self.graph_manager)
        
        # Initialize Tracking and Context Managers
        self.tracking_manager = TrackingManager(self.script_dir)
        self.experiment_manager = ExperimentManager() # Uses tracking_manager internally but we can re-instantiate or share if needed.
        # ExperimentManager currently instantiates its own TrackingManager. 
        # Ideally we share instances, but since JSONL is the source of truth, separate instances are fine for now.
        
        self.context_manager = ContextManager(
            base_dir=self.script_dir,
            graph_manager=self.graph_manager,
            tracking_manager=self.tracking_manager
        )
        
        # Initialize Skill Loader for YAML-based behavior
        self.skill_loader = SkillLoader(os.path.join(self.script_dir, "skills"))
        self.current_stage = "experience"  # Track Kolb stage

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
    
    def _run_grounding_protocol(self):
        """Mandatory grounding protocol for frontal cortex reset."""
        grounding = self.skill_loader.get_grounding_config()
        if not grounding:
            return  # No grounding config found
        
        print("\n" + "="*50)
        print("  GROUNDING (15 seconds)")
        print("="*50)
        
        # Step 1: Physiological Sigh
        step1 = grounding.get('sequence', {}).get('1_physiological_sigh', {})
        print(f"\n{step1.get('instruction', 'Take a deep breath...')}")
        input("\nPress Enter after your exhale...")
        
        # Step 2: Micro Anchor
        step2 = grounding.get('sequence', {}).get('2_micro_anchor', {})
        print(f"\n{step2.get('instruction', 'Notice your surroundings...')}")
        input("\nPress Enter to continue...")
        
        print("\n✓ Grounded. Let's begin.\n")
    
    def _build_experiment_context(self) -> str:
        """Build experiment context with guardrails."""
        active_experiments = self.tracking_manager.get_active_experiments()
        count = len(active_experiments)
        
        # Check for limit message
        limit_msg = self.skill_loader.get_experiment_limit_message(count)
        
        context_parts = []
        if limit_msg:
            context_parts.append(f"EXPERIMENT GUARDRAIL:\n{limit_msg}")
        
        if count > 0:
            context_parts.append(f"\nACTIVE EXPERIMENTS ({count}):")
            for exp in active_experiments[:3]:  # Show max 3
                context_parts.append(f"  - {exp.title}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _check_grounding_offer(self, text: str) -> bool:
        """Check if we should offer grounding based on physical sensation triggers."""
        return self.skill_loader.check_physical_sensation_triggers(text)

    # --- MODES ---

    def run_daily_reflection(self):
        print("\n=== DAILY REFLECTION (Kolb Cycle) ===")
        
        # MANDATORY: Run grounding protocol first
        self._run_grounding_protocol()
        
        kolb_template = self.load_kolb_template()
        
        # Show any experiments needing follow-up
        needs_followup = self.tracking_manager.get_experiments_needing_followup()
        if needs_followup:
            print("\n📋 Experiments to follow up on:")
            for exp in needs_followup:
                progress = exp.cumulative_progress()
                print(f"  • {exp.title} (progress: {'+' if progress >= 0 else ''}{progress})")
        
        # Initial input
        initial_thought = self._get_multiline_input("What's on your mind?")
        if not initial_thought: return

        history = []
        user_input = initial_thought
        self.current_stage = "experience"  # Reset stage tracking
        
        print("\nStarting Coach Session (Type 'EXIT' to cancel, 'SAVE' to finish)...")

        while True:
            # 1. Build rich context using Context Manager
            session_ctx = self.context_manager.build_session_context(user_input)
            
            # 2. Format hierarchical context
            hierarchical_context = self.context_manager.get_full_context_block(user_input)
            
            # 3. Get stage-specific rules from skills
            stage_rules = self.skill_loader.build_stage_prompt_context(self.current_stage)
            
            # 4. Build experiment context with guardrails
            experiment_context = self._build_experiment_context()
            
            # 5. Check if we should offer grounding (mid-session)
            if self._check_grounding_offer(user_input) and len(history) > 0:
                # Add grounding offer to stage rules
                observation = self.skill_loader.get_stage_config('observation')
                if observation:
                    grounding_offer = observation.get('on_physical_sensation', '')
                    stage_rules += f"\n\nGROUNDING OFFER (user mentioned physical sensation):\n{grounding_offer}"
            
            # 6. Dynamic Prompting with enhanced context
            prompt_text = DAILY_GUIDANCE_PROMPT.format(
                current_step=self.current_stage.title(),
                hierarchical_context=hierarchical_context,
                graph_context=session_ctx.graph_context or "No specific past context found.",
                stage_rules=stage_rules,
                experiment_context=experiment_context
            )
            
            # 4. LLM Response
            ai_msg = self._call_llm(prompt_text, user_input, history)
            print(f"\nCoach: {ai_msg}")

            # Add to history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ai_msg})

            # Get Next Input
            user_input = self._get_multiline_input("You")
            
            # Check for exit/cancel commands
            if user_input.strip().upper() in ['SAVE', 'DONE']:
                break
            if user_input.strip().upper() == 'EXIT' or not user_input.strip():
                print("\nSession cancelled. No data saved.")
                return  # Exit without saving
        
        # Generate Summary
        print("\nGenerating Summary...")
        full_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        summary_raw = self._call_llm(DAILY_SUMMARY_PROMPT, full_text)
        
        data = {}
        try:
            summary_clean = self._strip_markdown_json(summary_raw)
            data = json.loads(summary_clean)
            self.save_daily_entry(data, full_text)
        except:
            print("Error parsing summary JSON. Saving raw text.")
            self.save_daily_entry({}, full_text)

        # Extract and save any new experiments
        print("\n[Experiment Tracker] Checking for new experiments...")
        self._extract_and_save_experiments(full_text)
        
        # Save session memory for continuity
        self.context_manager.save_session_memory(
            summary=data.get("summary", "Session completed"),
            open_loops=[data.get("proposed_solution", "")] if data.get("proposed_solution") else [],
            emotional_state="",
            next_focus=data.get("key_takeaway", "")
        )

        # Post-Session Graph Ingestion
        print("\n[Graph Manager] Ingesting full session into Psyche Graph...")
        self.ingestion_pipeline.process_session(full_text)
        self.graph_manager.save_graph()
        print("[Graph Manager] Ingestion Complete.")
    
    def _extract_and_save_experiments(self, full_text: str):
        """Extract experiments from conversation and save to tracking system."""
        try:
            exp_raw = self._call_llm(EXPERIMENT_EXTRACTION_PROMPT, full_text)
            exp_clean = self._strip_markdown_json(exp_raw)
            exp_data = json.loads(exp_clean)
            
            if exp_data.get("experiment_found", False):
                exp = self.tracking_manager.create_experiment(
                    title=exp_data.get("title", "New experiment"),
                    description=exp_data.get("description", ""),
                    success_criteria=exp_data.get("success_criteria", "")
                )
                print(f"  ✓ Created experiment: {exp.title}")
            else:
                print("  No new experiment detected.")
        except Exception as e:
            print(f"  Could not extract experiment: {e}")

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
        # Retrieve Graph Context (same as daily reflection)
            anchors = self.graph_manager.find_nodes_by_text(user_input)
            anchor_ids = [n['id'] for n in anchors]
            graph_context = self.graph_manager.ego_walk(anchor_ids[:3]) if anchor_ids else "No specific past patterns found."
            # Inject context into system prompt
            sys_prompt = WEEKLY_SYSTEM_PROMPT.format(
                prev_context=json.dumps(past_context), 
                current_data=current_data,
                graph_context=graph_context
            )
            
            ### LLM response 
            ai_msg = self._call_llm(sys_prompt, user_input, history)
            print(f"\nCoach: {ai_msg}")
            
            ### Add to history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ai_msg})
            
            ### Get Next Input
            user_input = self._get_multiline_input("You")
            
            # Check for exit/cancel commands
            if user_input.strip().upper() in ['SAVE', 'DONE']:
                break
            if user_input.strip().upper() == 'EXIT' or not user_input.strip():
                print("\nSession cancelled. No data saved.")
                return  # Exit without saving
        
        # 3. Generate Progression Summary
        print("\nCreating building blocks for next week...")
        full_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        summary_raw = self._call_llm(WEEKLY_SUMMARY_PROMPT, full_text)
        
        try:
            # Clean up potential markdown formatting
            summary_clean = self._strip_markdown_json(summary_raw)
            summary_json = json.loads(summary_clean)
            self.save_weekly_context(summary_json)
            print(f"\nNext Week's Focus: {summary_json.get('focus_for_next_week')}")
        except:
            print("Could not generate structured weekly summary.")
        
        #4. Post-Session Graph Ingestion
        print("\n[Graph Manager] Ingesting full session into Psyche Graph...")
        self.ingestion_pipeline.process_session(full_text)
        self.graph_manager.save_graph()
        print("[Graph Manager] Ingestion Complete.")

    def run_goal_management(self):
        """Interactive goal and habit management."""
        while True:
            print("\n=== GOAL & HABIT MANAGEMENT ===")
            
            # Show current goals
            goals = self.tracking_manager.get_active_goals()
            habits = self.tracking_manager.get_active_habits()
            experiments = self.tracking_manager.get_active_experiments()
            
            print(f"\n📊 Current Status:")
            print(f"   Goals: {len(goals)} | Habits: {len(habits)} | Experiments: {len(experiments)}")
            
            if goals:
                print("\n🎯 Active Goals:")
                for i, g in enumerate(goals, 1):
                    print(f"   {i}. {g.title}")
                    for h in self.tracking_manager.get_habits_for_goal(g.id):
                        print(f"      └─ {h.title}")
            
            print("\n--- Options ---")
            print("1: Create New Goal (6-12 month vision)")
            print("2: Add Habit to Goal")
            print("3: View Progress Summary")
            print("4: Log Experiment Progress")
            print("5: Delete Goal/Habit")
            print("6: Back to Main Menu")
            
            choice = input("\nSelect: ").strip()
            
            if choice == '1':
                self._create_goal_interactive()
            elif choice == '2':
                self._add_habit_interactive()
            elif choice == '3':
                self._show_progress_summary()
            elif choice == '4':
                self._log_progress_interactive()
            elif choice == '5':
                self._delete_item_interactive()
            elif choice == '6':
                break
    
    def _create_goal_interactive(self):
        """Create a new target goal interactively."""
        print("\n--- Create New Goal ---")
        print("Think about: What kind of person do you want to become in 6-12 months?")
        print("Example: 'Emotionally regulated person who responds thoughtfully to triggers'\n")
        
        title = input("Goal title: ").strip()
        if not title:
            print("Cancelled.")
            return
        
        description = self._get_multiline_input("Describe this person (what habits would they have?)")
        if not description:
            print("Cancelled.")
            return
            
        target_date = input("Target date (YYYY-MM-DD, or press Enter for 6 months): ").strip()
        
        if not target_date:
            target_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        
        goal = self.tracking_manager.create_goal(title, description, target_date)
        print(f"\n✓ Created goal: {goal.title}")
        print(f"  Target date: {target_date}")
        
        # Offer LLM-assisted habit breakdown
        print("\nWould you like me to suggest habits for this goal using AI?")
        use_ai = input("(y/n): ").strip().lower()
        
        if use_ai == 'y':
            self._llm_habit_breakdown(goal)
        else:
            print("\nWould you like to add habits manually?")
            if input("(y/n): ").strip().lower() == 'y':
                self._add_habit_interactive(goal.id)
    
    def _llm_habit_breakdown(self, goal):
        """Interactive LLM session to collaboratively develop habits for a goal."""
        print("\n🤖 Starting collaborative habit development session...")
        print("(Type 'DONE' or 'FINALIZE' when ready to save habits, 'EXIT' to cancel)\n")
        
        system_prompt = HABIT_DEVELOPMENT_PROMPT.format(
            goal_title=goal.title,
            goal_description=goal.description
        )
        
        history = []
        user_input = "Let's work together to break down this goal into habits."
        
        while True:
            # Get LLM response
            ai_msg = self._call_llm(system_prompt, user_input, history)
            print(f"\nCoach: {ai_msg}")
            
            # Add to history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ai_msg})
            
            # Get next user input
            user_input = self._get_multiline_input("You")
            
            # Check for exit/done commands
            if not user_input.strip():
                print("\nSession cancelled. No habits saved.")
                return
            
            cmd = user_input.strip().upper()
            if cmd == 'EXIT':
                print("\nSession cancelled. No habits saved.")
                return
            elif cmd in ['DONE', 'FINALIZE', 'SAVE']:
                break
        
        # Ask LLM to generate final JSON summary
        print("\n📋 Generating final habit list...")
        finalize_prompt = """Based on our conversation, output ONLY a JSON array of the habits we discussed:
```json
[
    {"title": "Habit name", "description": "Description", "components": ["Skill 1", "Skill 2"]}
]
```
Include only the habits that were agreed upon."""
        
        final_response = self._call_llm(system_prompt, finalize_prompt, history)
        
        try:
            habits_data = json.loads(self._strip_markdown_json(final_response))
            
            print(f"\n📋 Habits developed for '{goal.title}':\n")
            for i, h in enumerate(habits_data, 1):
                print(f"  {i}. {h['title']}")
                print(f"     {h.get('description', '')}")
                if h.get('components'):
                    print(f"     Components: {', '.join(h['components'])}")
                print()
            
            # Confirm which to save
            print("Which habits would you like to save? (numbers like '1,2,3', 'all', or 'none')")
            selection = input("Selection: ").strip().lower()
            
            if selection == 'none':
                print("No habits saved.")
                return
            elif selection == 'all':
                indices = list(range(len(habits_data)))
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(",")]
                except ValueError:
                    print("Invalid selection. No habits saved.")
                    return
            
            # Create selected habits
            for idx in indices:
                if 0 <= idx < len(habits_data):
                    h = habits_data[idx]
                    habit = self.tracking_manager.create_habit(
                        title=h['title'],
                        description=h.get('description', ''),
                        goal_id=goal.id,
                        components=h.get('components', [])
                    )
                    print(f"  ✓ Saved: {habit.title}")
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"\nCould not parse final habits. Here's what the AI said:")
            print(final_response[:500])
            print("\nYou can add habits manually from the main menu.")
    
    def _add_habit_interactive(self, goal_id: str = None):
        """Add a habit to a goal - manually or with AI assistance."""
        print("\n--- Add Habit ---")
        
        # Select goal if not provided
        goal = None
        if not goal_id:
            goals = self.tracking_manager.get_active_goals()
            if not goals:
                print("No goals yet. Create a goal first.")
                return
            
            print("Select a goal:")
            for i, g in enumerate(goals, 1):
                print(f"  {i}. {g.title}")
            
            try:
                idx = int(input("Goal number: ")) - 1
                goal = goals[idx]
                goal_id = goal.id
            except (ValueError, IndexError):
                print("Invalid selection.")
                return
        else:
            goal = self.tracking_manager.get_goal(goal_id)
        
        # Show existing habits for this goal
        existing_habits = self.tracking_manager.get_habits_for_goal(goal_id)
        if existing_habits:
            print(f"\nExisting habits for '{goal.title}':")
            for h in existing_habits:
                print(f"  • {h.title}")
        
        # Ask for approach
        print("\nHow would you like to add habits?")
        print("  1: Manual entry")
        print("  2: AI-assisted (discuss with coach)")
        choice = input("Select: ").strip()
        
        if choice == '2':
            self._ai_habit_session(goal, existing_habits)
            return
        
        # Manual entry
        print("\nWhat habit does this person have?")
        print("Example: 'Recognize emotional overload before reacting'\n")
        
        title = input("Habit title: ").strip()
        if not title:
            print("Cancelled.")
            return
        
        description = input("Brief description: ").strip()
        
        components_input = input("Component skills (comma-separated, or Enter to skip): ").strip()
        components = [c.strip() for c in components_input.split(",")] if components_input else []
        
        habit = self.tracking_manager.create_habit(title, description, goal_id, components)
        print(f"\n✓ Created habit: {habit.title}")
        if components:
            print(f"  Components: {', '.join(components)}")
    
    def _ai_habit_session(self, goal, existing_habits):
        """AI-assisted session to develop/refine habits with context."""
        print("\n🤖 Starting AI-assisted habit session...")
        print("(Type 'DONE' to finalize, 'EXIT' to cancel)\n")
        
        # Build context about existing habits
        habits_context = ""
        if existing_habits:
            habits_context = "EXISTING HABITS:\n" + "\n".join(
                f"- {h.title}: {h.description}" for h in existing_habits
            )
        else:
            habits_context = "No habits defined yet for this goal."
        
        system_prompt = f"""You are a performance coach helping refine habits for a goal.

GOAL: {goal.title}
DESCRIPTION: {goal.description}

{habits_context}

Your role:
- Help add new habits or refine existing ones
- Identify gaps in the current habit structure
- Suggest component skills for each habit
- Be collaborative and build on the user's ideas

When user says 'DONE', output final NEW habits as JSON:
```json
[{{"title": "Habit", "description": "...", "components": ["..."]}}]
```"""
        
        history = []
        user_input = "Let's work on habits for this goal."
        
        while True:
            ai_msg = self._call_llm(system_prompt, user_input, history)
            print(f"\nCoach: {ai_msg}")
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ai_msg})
            
            user_input = self._get_multiline_input("You")
            
            if not user_input.strip() or user_input.strip().upper() == 'EXIT':
                print("\nSession cancelled.")
                return
            if user_input.strip().upper() in ['DONE', 'SAVE']:
                break
        
        # Get final habits
        print("\n📋 Generating habit list...")
        final = self._call_llm(system_prompt, 
            "Output only the NEW habits we discussed as JSON array.", history)
        
        try:
            habits_data = json.loads(self._strip_markdown_json(final))
            if not habits_data:
                print("No new habits to add.")
                return
                
            print("\nNew habits to add:")
            for i, h in enumerate(habits_data, 1):
                print(f"  {i}. {h['title']}")
            
            print("\nSave these? (y/n)")
            if input().strip().lower() == 'y':
                for h in habits_data:
                    habit = self.tracking_manager.create_habit(
                        h['title'], h.get('description', ''),
                        goal.id, h.get('components', [])
                    )
                    print(f"  ✓ Saved: {habit.title}")
        except:
            print("Could not parse habits. Add manually if needed.")
    
    def _show_progress_summary(self):
        """Show overall progress summary."""
        print("\n--- Progress Summary ---")
        summary = self.tracking_manager.get_overall_progress_summary()
        print(summary)
        
        # Show detailed experiment progress
        experiments = self.tracking_manager.get_active_experiments()
        if experiments:
            print("\n📈 Experiment Details:")
            for exp in experiments:
                gains = self.tracking_manager.calculate_marginal_gains(exp.id)
                status = "🟢" if gains.get("near_completion") else "🔵"
                print(f"  {status} {exp.title}")
                print(f"      Progress: {gains.get('total_progress', 0):+d} | "
                      f"Days: {gains.get('successful_days', 0)}/7")
    
    def _log_progress_interactive(self):
        """Log progress on an active experiment."""
        print("\n--- Log Experiment Progress ---")
        
        experiments = self.tracking_manager.get_active_experiments()
        if not experiments:
            print("No active experiments to log progress for.")
            return
        
        print("Select experiment:")
        for i, exp in enumerate(experiments, 1):
            progress = exp.cumulative_progress()
            print(f"  {i}. {exp.title} (current: {progress:+d})")
        
        try:
            idx = int(input("Experiment number: ")) - 1
            exp = experiments[idx]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
        
        print(f"\nLogging progress for: {exp.title}")
        print("Outcome options: success, partial, not_tried, failed")
        outcome = input("Outcome: ").strip().lower()
        if outcome not in ("success", "partial", "not_tried", "failed"):
            outcome = "partial"
        
        notes = input("Notes (what happened?): ").strip()
        
        print("Marginal gain score (-3 to +3):")
        print("  -3 = Major setback | 0 = No change | +3 = Major progress")
        try:
            score = int(input("Score: "))
        except ValueError:
            score = 0
        
        self.tracking_manager.log_progress(exp.id, outcome, notes, score)
        print(f"\n✓ Progress logged! New total: {exp.cumulative_progress():+d}")
    
    def _delete_item_interactive(self):
        """Delete a goal or habit."""
        print("\n--- Delete Goal/Habit ---")
        print("1: Delete a Goal (and its habits)")
        print("2: Delete a Habit only")
        print("3: Cancel")
        
        choice = input("Select: ").strip()
        
        if choice == '1':
            goals = self.tracking_manager.get_active_goals()
            if not goals:
                print("No goals to delete.")
                return
            
            print("\nSelect goal to delete:")
            for i, g in enumerate(goals, 1):
                habits = self.tracking_manager.get_habits_for_goal(g.id)
                print(f"  {i}. {g.title} ({len(habits)} habits)")
            
            try:
                idx = int(input("Goal number: ")) - 1
                goal = goals[idx]
            except (ValueError, IndexError):
                print("Invalid selection.")
                return
            
            print(f"\n⚠️  Delete '{goal.title}' and all its habits?")
            if input("Type 'yes' to confirm: ").strip().lower() == 'yes':
                self.tracking_manager.delete_goal(goal.id)
                print(f"✓ Deleted goal: {goal.title}")
            else:
                print("Cancelled.")
                
        elif choice == '2':
            habits = self.tracking_manager.get_active_habits()
            if not habits:
                print("No habits to delete.")
                return
            
            print("\nSelect habit to delete:")
            for i, h in enumerate(habits, 1):
                print(f"  {i}. {h.title}")
            
            try:
                idx = int(input("Habit number: ")) - 1
                habit = habits[idx]
            except (ValueError, IndexError):
                print("Invalid selection.")
                return
            
            print(f"\n⚠️  Delete habit '{habit.title}'?")
            if input("Type 'yes' to confirm: ").strip().lower() == 'yes':
                self.tracking_manager.delete_habit(habit.id)
                print(f"✓ Deleted habit: {habit.title}")
    
    def run_experiments_session(self):
        """Interactive session to run protocols."""
        while True:
            print("\n🧪 EXPERIMENTS & PROTOCOLS")
            print("=========================")
            
            experiments = self.tracking_manager.get_active_experiments()
            
            print("1. Vent & Reframe (Emotional Regulation)")
            
            # Show user experiments
            for i, exp in enumerate(experiments, 1):
                print(f"{i+1}. {exp.title}")
            
            print(f"{len(experiments)+2}. Back to Main Menu")
            
            choice = input("\nSelect protocol to run: ").strip()
            
            if choice == '1':
                self.run_vent_reframe()
            elif choice == str(len(experiments)+2):
                break
            else:
                try:
                    idx = int(choice) - 2
                    if 0 <= idx < len(experiments):
                        exp = experiments[idx]
                        # Use the experiment manager's nudge feature
                        self.experiment_manager.nudge(exp.id)
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")

    def run_vent_reframe(self):
        """
        Vent & Reframe Protocol - 5-step emotional regulation.
        Based on experiment exp_35599818 (Frustration Decoder & Reframe).
        """
        print("\n" + "="*60)
        print("   VENT & REFRAME PROTOCOL")
        print("   Frustration Decoder & Positive Counter")
        print("="*60)
        
        # Step 1: Detect & Label
        print("\n--- Step 1: Detect & Label ---")
        print("Rate your current chest/stomach tension (1=mild, 5=intense)")
        try:
            pre_tension = int(input("Tension level (1-5): ").strip())
            if not 1 <= pre_tension <= 5:
                pre_tension = 3
        except ValueError:
            pre_tension = 3
        
        print(f"\n🔴 Frustration Signal Detected")
        print(f"Current tension level: {pre_tension}/5")
        print(f"{'█' * pre_tension}{'░' * (5 - pre_tension)}")
        print("\nTake a moment to acknowledge this feeling without judgment.")
        
        # Step 2 & 3: Vent and Decode
        print("\n--- Step 2-3: Vent & Decode ---")
        vent_text = self._get_multiline_input("Vent freely (what's frustrating you?)")
        
        if not vent_text or vent_text.strip().upper() == 'EXIT':
            print("\nSession cancelled.")
            return
        
        print("\nAnalyzing your frustration...")
        decode_prompt = VENT_DECODE_PROMPT.format(vent_text=vent_text)
        decode_raw = self._call_llm(decode_prompt, vent_text)
        
        try:
            decode_data = json.loads(self._strip_markdown_json(decode_raw))
        except json.JSONDecodeError:
            print("Could not analyze. Please try again.")
            return
        
        underlying_need = decode_data.get("underlying_need", "")
        need_category = decode_data.get("need_category", "unknown")
        triggers = decode_data.get("triggers", [])
        
        print(f"\n🔍 Need Decoded")
        print(f"\nCategory: {need_category.upper()}")
        print(f"Core unmet need: {decode_data.get('unmet_need_summary', 'N/A')}")
        print(f"\nUnderlying need: {underlying_need}")
        print(f"\nTriggers identified:")
        for t in triggers:
            print(f"  • {t}")
        print(f"\nConfidence: {decode_data.get('confidence', 0):.0%}")
        
        # Step 4: Reframe
        print("\n--- Step 4: Reframe ---")
        reframe_prompt = VENT_REFRAME_PROMPT.format(
            underlying_need=underlying_need,
            need_category=need_category,
            vent_text=vent_text
        )
        reframe_raw = self._call_llm(reframe_prompt, vent_text)
        
        try:
            reframe_data = json.loads(self._strip_markdown_json(reframe_raw))
        except json.JSONDecodeError:
            reframe_data = {"reframe_question": "What is one small step I can take right now?"}
        
        reframe_question = reframe_data.get("reframe_question", "")
        print(f"\n💡 Reframe Question")
        print(f"\nAddressing your need for {need_category}, ask yourself:")
        print(f'\n    "{reframe_question}"')
        print(f"\nWhy this helps: {reframe_data.get('why_this_helps', 'N/A')}")
        
        # Step 5: Micro-action
        print("\n--- Step 5: Micro-Action ---")
        action_prompt = VENT_MICRO_ACTION_PROMPT.format(
            reframe_question=reframe_question,
            underlying_need=underlying_need,
            need_category=need_category
        )
        action_raw = self._call_llm(action_prompt, reframe_question)
        
        try:
            action_data = json.loads(self._strip_markdown_json(action_raw))
        except json.JSONDecodeError:
            action_data = {"micro_action": "Take 5 minutes to write down what you need."}
        
        micro_action = action_data.get("micro_action", "")
        print(f"\n⚡ Your Micro-Action (5 minutes)")
        print(f"\n→ {micro_action}")
        print(f"\nTime needed: {action_data.get('time_estimate', '5 minutes')}")
        print(f"How this meets your need: {action_data.get('expected_outcome', 'N/A')}")
        
        input("\nPress Enter after attempting the micro-action...")
        
        # Step 6: Post-tension
        print("\n--- Final: Capture Results ---")
        try:
            post_tension = int(input("Tension level now (1-5): ").strip())
            if not 1 <= post_tension <= 5:
                post_tension = pre_tension
        except ValueError:
            post_tension = pre_tension
        
        action_taken = input("Did you take the action? (y/n): ").strip().lower() == 'y'
        notes = input("Any notes? (Enter to skip): ").strip()
        
        delta = pre_tension - post_tension
        delta_str = f"+{abs(delta)} improvement" if delta > 0 else f"{abs(delta)} increase" if delta < 0 else "no change"
        
        print(f"\n✅ Session Complete")
        print(f"\nTension Before: {pre_tension}/5 {'█' * pre_tension}{'░' * (5 - pre_tension)}")
        print(f"Tension After:  {post_tension}/5 {'█' * post_tension}{'░' * (5 - post_tension)}")
        print(f"Change: {delta_str}")
        print(f"\nNeed category: {need_category}")
        print(f"Action taken: {'Yes ✓' if action_taken else 'Not yet'}")
        
        # Log to experiment if exists
        experiments = self.tracking_manager.get_active_experiments()
        vent_exp = next((e for e in experiments if 'vent' in e.title.lower() or 'reframe' in e.title.lower()), None)
        
        if vent_exp:
            outcome = "success" if delta > 0 else "partial" if delta == 0 else "not_tried"
            self.tracking_manager.log_progress(
                vent_exp.id,
                outcome=outcome,
                notes=f"Need: {need_category}. {notes}",
                marginal_gain_score=min(3, max(-3, delta))
            )
            print(f"\n📊 Progress logged to experiment: {vent_exp.title}")
        
        # Save session memory
        self.context_manager.save_session_memory(
            summary=f"Vent & Reframe: {need_category} - {decode_data.get('unmet_need_summary', 'processed')}",
            open_loops=[reframe_question] if not action_taken else [],
            emotional_state=f"Tension {pre_tension}→{post_tension}",
            next_focus=micro_action if not action_taken else ""
        )
        print("\n[Context] Session saved.")


if __name__ == "__main__":
    agent = ReflectionCoach()
    
    while True:
        print("\n╔══════════════════════════════════╗")
        print("║   REFLECTION COACH               ║")
        print("╠══════════════════════════════════╣")
        print("║  1: Daily Reflection             ║")
        print("║  2: Weekly Review                ║")
        print("║  3: Goal & Habit Management      ║")
        print("║  4: Experiments & Protocols      ║")
        print("║  5: Exit                         ║")
        print("╚══════════════════════════════════╝")
        choice = input("Select: ")
        
        if choice == '1': agent.run_daily_reflection()
        elif choice == '2': agent.run_weekly_review()
        elif choice == '3': agent.run_goal_management()
        elif choice == '4': agent.run_experiments_session()
        elif choice == '5': break