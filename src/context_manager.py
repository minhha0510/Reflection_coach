"""
Context Manager for LLM Reflection Sessions
============================================
Builds rich context windows for reflection prompts by combining:
- Active goals and habits
- Experiments needing follow-up
- Last session summary
- Graph context via ego_walk
- Weekly focus
- Marginal gains status
"""

import os
import json
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from .tracking_manager import TrackingManager
from .tracking_schema import TargetGoal, Habit, Experiment


@dataclass
class SessionContext:
    """Container for all context needed by LLM during a reflection session."""
    active_goals: List[TargetGoal] = field(default_factory=list)
    habits_in_focus: List[Habit] = field(default_factory=list)
    experiments_needing_followup: List[Experiment] = field(default_factory=list)
    last_session_summary: Dict[str, Any] = field(default_factory=dict)
    graph_context: str = ""
    weekly_focus: str = ""
    suggested_followups: List[str] = field(default_factory=list)


class ContextManager:
    """
    Builds and manages context windows for reflection sessions.
    Combines tracking data, graph context, and session memory.
    """
    
    def __init__(self, base_dir: Optional[str] = None, 
                 graph_manager=None, tracking_manager=None):
        """
        Initialize context manager.
        
        Args:
            base_dir: Base directory for data files
            graph_manager: Optional GraphManager instance
            tracking_manager: Optional TrackingManager instance
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.base_dir = base_dir
        self.last_session_file = os.path.join(base_dir, "last_session.json")
        self.weekly_context_file = os.path.join(base_dir, "weekly", "context_memory.json")
        
        # Use provided managers or create new ones
        self.tracking_manager = tracking_manager or TrackingManager(base_dir)
        self.graph_manager = graph_manager
    
    def set_graph_manager(self, graph_manager):
        """Set or update the graph manager."""
        self.graph_manager = graph_manager
    
    # ==================== SESSION MEMORY ====================
    
    def load_last_session(self) -> Dict[str, Any]:
        """Load the last session summary."""
        if os.path.exists(self.last_session_file):
            try:
                with open(self.last_session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def save_session_memory(self, summary: str, open_loops: List[str] = None,
                            emotional_state: str = "", 
                            next_focus: str = "") -> None:
        """
        Save session memory for continuity.
        
        Args:
            summary: Brief summary of this session
            open_loops: Questions/topics to follow up on
            emotional_state: User's emotional state at end of session
            next_focus: Suggested focus for next session
        """
        active_exp_ids = [e.id for e in self.tracking_manager.get_active_experiments()]
        
        session_data = {
            "date": date.today().isoformat(),
            "summary": summary,
            "open_loops": open_loops or [],
            "active_experiment_ids": active_exp_ids,
            "emotional_state": emotional_state,
            "next_session_focus": next_focus
        }
        
        with open(self.last_session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)
    
    def load_weekly_focus(self) -> str:
        """Load the weekly focus from context_memory.json."""
        if os.path.exists(self.weekly_context_file):
            try:
                with open(self.weekly_context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("focus_for_next_week", "")
            except (json.JSONDecodeError, IOError):
                pass
        return ""
    
    # ==================== CONTEXT BUILDING ====================
    
    def build_session_context(self, user_input: str = "") -> SessionContext:
        """
        Build complete session context for LLM prompt injection.
        
        Args:
            user_input: User's initial input (used for graph anchoring)
        
        Returns:
            SessionContext with all relevant context assembled
        """
        context = SessionContext()
        
        # 1. Get active goals and habits
        context.active_goals = self.tracking_manager.get_active_goals()
        context.habits_in_focus = self.tracking_manager.get_active_habits()
        
        # 2. Get experiments needing follow-up
        context.experiments_needing_followup = (
            self.tracking_manager.get_experiments_needing_followup()
        )
        
        # 3. Load last session summary
        context.last_session_summary = self.load_last_session()
        
        # 4. Load weekly focus
        context.weekly_focus = self.load_weekly_focus()
        
        # 5. Get graph context via ego_walk (if graph manager available)
        if self.graph_manager and user_input:
            anchors = self.graph_manager.find_nodes_by_text(user_input)
            anchor_ids = [n['id'] for n in anchors[:3]]
            if anchor_ids:
                context.graph_context = self.graph_manager.ego_walk(anchor_ids)
            else:
                context.graph_context = "No specific past context found."
        
        # 6. Generate suggested follow-ups
        context.suggested_followups = self._generate_followup_suggestions(context)
        
        return context
    
    def _generate_followup_suggestions(self, context: SessionContext) -> List[str]:
        """Generate natural language follow-up suggestions."""
        suggestions = []
        
        # Follow up on experiments
        for exp in context.experiments_needing_followup[:3]:
            progress = exp.cumulative_progress()
            progress_str = f"progress: {'+' if progress >= 0 else ''}{progress}"
            suggestions.append(
                f"How did the '{exp.title}' experiment go? ({progress_str})"
            )
        
        # Check open loops from last session
        last_session = context.last_session_summary
        if last_session.get("open_loops"):
            for loop in last_session["open_loops"][:2]:
                suggestions.append(f"Last time we discussed: {loop}")
        
        return suggestions
    
    # ==================== PROMPT FORMATTING ====================
    
    def format_goals_for_prompt(self, goals: List[TargetGoal]) -> str:
        """Format goals for LLM prompt injection."""
        if not goals:
            return "No active goals set."
        
        lines = []
        for g in goals[:3]:
            lines.append(f"- {g.title}: {g.description[:100]}...")
        return "\n".join(lines)
    
    def format_habits_for_prompt(self, habits: List[Habit]) -> str:
        """Format habits for LLM prompt injection."""
        if not habits:
            return "No habits in development."
        
        lines = []
        for h in habits[:5]:
            components = ", ".join(h.components[:3]) if h.components else "N/A"
            lines.append(f"- {h.title} (components: {components})")
        return "\n".join(lines)
    
    def format_experiments_for_prompt(self, experiments: List[Experiment]) -> str:
        """Format experiments needing follow-up for LLM prompt injection."""
        if not experiments:
            return "No experiments needing follow-up."
        
        lines = []
        for e in experiments:
            progress = e.cumulative_progress()
            days = e.successful_days()
            lines.append(
                f"- {e.title} | Progress: {'+' if progress >= 0 else ''}{progress} | "
                f"Successful days: {days}/7 | Criteria: {e.success_criteria[:50]}..."
            )
        return "\n".join(lines)
    
    def format_marginal_gains_summary(self) -> str:
        """Generate overall marginal gains summary."""
        return self.tracking_manager.get_overall_progress_summary()
    
    def get_full_context_block(self, user_input: str = "") -> str:
        """
        Generate the complete context block for prompt injection.
        
        Returns:
            Formatted string ready for LLM system prompt injection
        """
        ctx = self.build_session_context(user_input)
        
        sections = []
        
        # Active Goals
        if ctx.active_goals:
            sections.append(
                f"ACTIVE GOALS:\n{self.format_goals_for_prompt(ctx.active_goals)}"
            )
        
        # Habits in Development
        if ctx.habits_in_focus:
            sections.append(
                f"HABITS IN DEVELOPMENT:\n{self.format_habits_for_prompt(ctx.habits_in_focus)}"
            )
        
        # Experiments Needing Follow-up
        if ctx.experiments_needing_followup:
            sections.append(
                f"EXPERIMENTS NEEDING FOLLOW-UP:\n"
                f"{self.format_experiments_for_prompt(ctx.experiments_needing_followup)}"
            )
        
        # Suggested Follow-ups
        if ctx.suggested_followups:
            sections.append(
                f"SUGGESTED FOLLOW-UPS:\n" + 
                "\n".join(f"- {s}" for s in ctx.suggested_followups)
            )
        
        # Weekly Focus
        if ctx.weekly_focus:
            sections.append(f"WEEKLY FOCUS:\n{ctx.weekly_focus}")
        
        # Graph Context
        if ctx.graph_context:
            sections.append(f"RELEVANT PAST CONTEXT:\n{ctx.graph_context}")
        
        return "\n\n".join(sections) if sections else "No prior context available."


# --- INLINE TESTS ---
if __name__ == "__main__":
    import sys
    import shutil
    
    if "--test" in sys.argv:
        print("Running context_manager tests...")
        
        # Create isolated test directory
        test_dir = os.path.join(os.path.dirname(__file__), "tests", "output")
        os.makedirs(test_dir, exist_ok=True)
        os.makedirs(os.path.join(test_dir, "weekly"), exist_ok=True)
        
        # Clean up previous test files
        for f in ["goals.jsonl", "habits.jsonl", "experiments.jsonl", 
                  "last_session.json"]:
            path = os.path.join(test_dir, f)
            if os.path.exists(path):
                os.remove(path)
        
        # Create test weekly context
        weekly_ctx = {"focus_for_next_week": "Morning ritual optimization"}
        with open(os.path.join(test_dir, "weekly", "context_memory.json"), 'w') as f:
            json.dump(weekly_ctx, f)
        
        # Initialize managers
        tm = TrackingManager(base_dir=test_dir)
        cm = ContextManager(base_dir=test_dir, tracking_manager=tm)
        
        # Create test data
        goal = tm.create_goal("Test Goal", "Description")
        habit = tm.create_habit("Test Habit", goal_id=goal.id)
        exp = tm.create_experiment("Test Experiment", habit_id=habit.id)
        
        # Set experiment to need follow-up
        exp.last_checked = "2025-12-01"
        tm._save_experiments()
        
        # Test session context building
        ctx = cm.build_session_context()
        assert len(ctx.active_goals) == 1, "Goals not loaded"
        assert len(ctx.habits_in_focus) == 1, "Habits not loaded"
        assert len(ctx.experiments_needing_followup) == 1, "Follow-up not detected"
        assert ctx.weekly_focus == "Morning ritual optimization", "Weekly focus not loaded"
        print("  ✓ Session context building")
        
        # Test follow-up suggestions
        assert len(ctx.suggested_followups) > 0, "No follow-up suggestions"
        assert "Test Experiment" in ctx.suggested_followups[0], "Experiment not in suggestions"
        print("  ✓ Follow-up suggestions")
        
        # Test session memory save/load
        cm.save_session_memory(
            summary="Discussed morning routine",
            open_loops=["How did breathing go?"],
            emotional_state="hopeful",
            next_focus="Follow up on experiment"
        )
        loaded = cm.load_last_session()
        assert loaded["summary"] == "Discussed morning routine", "Session not saved"
        assert "How did breathing go?" in loaded["open_loops"], "Open loops not saved"
        print("  ✓ Session memory persistence")
        
        # Test full context block
        block = cm.get_full_context_block()
        assert "ACTIVE GOALS" in block, "Goals not in context block"
        assert "EXPERIMENTS NEEDING FOLLOW-UP" in block, "Experiments not in block"
        assert "WEEKLY FOCUS" in block, "Weekly focus not in block"
        print("  ✓ Full context block generation")
        
        # Test formatting methods
        goals_fmt = cm.format_goals_for_prompt(ctx.active_goals)
        assert "Test Goal" in goals_fmt, "Goal formatting failed"
        
        habits_fmt = cm.format_habits_for_prompt(ctx.habits_in_focus)
        assert "Test Habit" in habits_fmt, "Habit formatting failed"
        
        exp_fmt = cm.format_experiments_for_prompt(ctx.experiments_needing_followup)
        assert "Test Experiment" in exp_fmt, "Experiment formatting failed"
        print("  ✓ Prompt formatting")
        
        print("\nAll context_manager tests passed! ✓")
    else:
        print("Usage: python context_manager.py --test")
