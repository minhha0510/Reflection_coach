
import argparse
import sys
import json
import os
import requests
import re
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Optional

# Add parent directory to path for imports when run as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.tracking_manager import TrackingManager
from src.tracking_schema import Experiment

# Load env immediately
load_dotenv()

# --- CONFIGURATION (Duplicate from LLM_reflection.py for standalone usage) ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

class SmartExperimentPlayer:
    """
    Handles the interactive playback of an experiment protocol.
    Parses text into steps and uses LLM for on-demand coaching.
    """
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key

    def parse_steps(self, description: str) -> List[str]:
        """Split description into actionable steps."""
        steps = []
        lines = description.split('\n')
        
        # Scenario A: Multiline list
        if len(lines) > 1:
            for line in lines:
                clean = line.strip()
                if clean:
                    # Remove leading numbers/bullets for display? 
                    # Actually keeping them is often helpful for context, 
                    # but let's try to detect if it's a list item.
                    steps.append(clean)
            return steps

        # Scenario B: Single line block
        # Split by number patterns like "1)", "2.", "3-"
        parts = re.split(r'(\d+[\.\)]\s)', description)
        if len(parts) > 1:
            current_step = ""
            for part in parts:
                if re.match(r'\d+[\.\)]\s', part):
                    if current_step: steps.append(current_step.strip())
                    current_step = part.strip() # Start new step with number
                else:
                    current_step += " " + part
            if current_step: steps.append(current_step.strip())
            return steps

        # Scenario C: Just text
        return [description.strip()]

    def ask_ai_coach(self, step_text: str, user_context: str = "") -> str:
        """Call DeepSeek for a quick tip."""
        if not self.api_key:
            return "AI Coach unavailable (Missing API Key)."

        system_prompt = (
            "You are an encouraging productivity coach. "
            "The user is stuck or asking for help on a specific step of an experiment protocol. "
            "Provide a ONE-SENTENCE, practical tip to move them forward. "
            "Be direct and empathetic."
        )
        user_prompt = f"Step: {step_text}\nUser says: {user_context}"

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"(AI Error: {str(e)})"

    def play(self, experiment: Experiment):
        print(f"\n> NUDGE: {experiment.title}")
        print("=" * 60)
        
        steps = self.parse_steps(experiment.description)
        total = len(steps)
        session_notes = []

        print(f"Goal: {experiment.success_criteria}")
        input("\n[Press Enter to Start Protocol]")

        for i, step in enumerate(steps, 1):
            while True:
                print("\n" + "-"*40)
                print(f"STEP {i}/{total}")
                print(f"👉 {step}")
                print("-" * 40)
                print("[Enter] Next | [?] Help | [Text] Add Note")
                
                user_input = input("   > ").strip()

                if user_input == "":
                    # Next step
                    break
                elif user_input == "?" or user_input.lower() == "help":
                    print("   🤖 calling coach...")
                    advice = self.ask_ai_coach(step, "I need help/motivation.")
                    print(f"   💡 COACH: {advice}")
                else:
                    # Treat as note or specific question
                    # Heuristic: if it ends with ?, ask AI. If not, log it.
                    if user_input.endswith("?"):
                         print("   🤖 calling coach...")
                         advice = self.ask_ai_coach(step, user_input)
                         print(f"   💡 COACH: {advice}")
                    else:
                        print("   📝 Note added.")
                        session_notes.append(f"Step {i}: {user_input}")

        print("\n🎉 Protocol Complete!")
        return "\n".join(session_notes)

class ExperimentManager:
    def __init__(self):
        self.tm = TrackingManager()
        self.player = SmartExperimentPlayer()

    def list_experiments(self, active_only: bool = True):
        experiments = self.tm.get_active_experiments() if active_only else self.tm._load_jsonl(self.tm.experiments_file)
        if hasattr(experiments, '__iter__') and not isinstance(experiments, list):
             experiments = list(experiments)
        
        if not active_only and experiments and isinstance(experiments[0], dict):
             experiments = [Experiment.from_dict(e) for e in experiments]

        if not experiments:
            print("No active experiments found.")
            return

        print(f"\n[LIST] Found {len(experiments)} experiments:")
        for i, exp in enumerate(experiments, 1):
            status_icon = "[ACT]" if exp.status == "active" else "[TST]" if exp.status == "testing" else "[...]"
            print(f"{i}. {status_icon} [{exp.id}] {exp.title}")
            print(f"   Goal: {exp.success_criteria[:60]}...")
            print(f"   Stats: {exp.successful_days()} successes | Score: {exp.cumulative_progress()}")

    def add_experiment(self, title: str, description: str, success_criteria: str, habit_id: Optional[str] = None):
        exp = self.tm.create_experiment(
            title=title,
            description=description,
            success_criteria=success_criteria,
            habit_id=habit_id
        )
        print(f"\n[+] Experiment Created: {exp.title} ({exp.id})")
        print(f"   Description: {exp.description}")

    def log_progress(self, exp_id: str, outcome: str, notes: str, score: int):
        if outcome not in ["success", "partial", "not_tried", "failed"]:
            print(f"Error: Invalid outcome '{outcome}'. Must be success|partial|not_tried|failed")
            return
        if not (-3 <= score <= 3):
            print(f"Error: Score {score} must be between -3 and +3")
            return

        try:
            self.tm.update_experiment(
                exp_id, 
                log_entry={
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "outcome": outcome,
                    "notes": notes,
                    "marginal_gain_score": score
                }
            )
            print(f"\n[OK] Logged entry for {exp_id}")
            print(f"   Outcome: {outcome} ({score})")
        except Exception as e:
            print(f"Error logging progress: {e}")

    def nudge(self, exp_id: str):
        """Interactive nudge using SmartExperimentPlayer."""
        exp = self.tm.get_experiment(exp_id)
        if not exp:
            print(f"Error: Experiment {exp_id} not found.")
            return

        # Delegate to Smart Player
        notes = self.player.play(exp)

        # Ask to log
        choice = input("\nLog this run? (y/n): ").strip().lower()
        if choice == 'y':
            outcome = input("Outcome (success/partial/failed/not_tried): ").strip()
            score = int(input("Marginal Gain Score (-3 to 3): ") or 0)
            user_notes = input("Additional Notes: ").strip()
            
            final_notes = f"{user_notes} | {notes}".strip(" |")
            self.log_progress(exp.id, outcome, final_notes, score)

def main():
    parser = argparse.ArgumentParser(description="Experiment Manager SKILL Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List
    parser_list = subparsers.add_parser("list", help="List active experiments")
    parser_list.add_argument("--all", action="store_true", help="Show all experiments including archived")

    # Add
    parser_add = subparsers.add_parser("add", help="Add a new experiment")
    parser_add.add_argument("--title", required=True)
    parser_add.add_argument("--desc", required=True, help="Description/Protocol")
    parser_add.add_argument("--criteria", required=True, help="Success criteria")
    parser_add.add_argument("--habit", help="Linked Habit ID")

    # Log
    parser_log = subparsers.add_parser("log", help="Log progress")
    parser_log.add_argument("id", help="Experiment ID")
    parser_log.add_argument("--outcome", required=True, choices=["success", "partial", "failed", "not_tried"])
    parser_log.add_argument("--score", type=int, required=True, help="Score -3 to 3")
    parser_log.add_argument("--notes", default="", help="Optional notes")

    # Nudge
    parser_nudge = subparsers.add_parser("nudge", help="Run interactive nudge")
    parser_nudge.add_argument("id", help="Experiment ID")

    args = parser.parse_args()
    mgr = ExperimentManager()

    if args.command == "list":
        mgr.list_experiments(active_only=not args.all)
    elif args.command == "add":
        mgr.add_experiment(args.title, args.desc, args.criteria, args.habit)
    elif args.command == "log":
        mgr.log_progress(args.id, args.outcome, args.notes, args.score)
    elif args.command == "nudge":
        mgr.nudge(args.id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
