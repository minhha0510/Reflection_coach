"""
Tracking Manager for Hierarchical Goal/Habit/Experiment System
===============================================================
Manages CRUD operations for:
- Target Goals (6-12 month vision)
- Habits (skills to develop)  
- Experiments (daily micro-tests)

All data stored in JSONL format for traceability and embedding support.
Supports bidirectional updates (reflections can reshape goals/habits).
"""

import os
import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from .tracking_schema import TargetGoal, Habit, Experiment, ProgressEntry


class TrackingManager:
    """
    Manages hierarchical tracking of goals, habits, and experiments.
    Data is stored in JSONL files for append-only traceability.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize tracking manager with storage paths."""
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.base_dir = base_dir
        self.goals_file = os.path.join(base_dir, "goals.jsonl")
        self.habits_file = os.path.join(base_dir, "habits.jsonl")
        self.experiments_file = os.path.join(base_dir, "experiments.jsonl")
        
        # In-memory caches (loaded from JSONL)
        self._goals: Dict[str, TargetGoal] = {}
        self._habits: Dict[str, Habit] = {}
        self._experiments: Dict[str, Experiment] = {}
        
        # Load existing data
        self._load_all()
    
    # ==================== PERSISTENCE ====================
    
    def _load_jsonl(self, filepath: str) -> List[Dict[str, Any]]:
        """Load all entries from a JSONL file."""
        entries = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        return entries
    
    def _append_jsonl(self, filepath: str, data: Dict[str, Any]):
        """Append a single entry to a JSONL file."""
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')
    
    def _rewrite_jsonl(self, filepath: str, entries: List[Dict[str, Any]]):
        """Rewrite entire JSONL file (for updates)."""
        with open(filepath, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
    
    def _load_all(self):
        """Load all data from JSONL files into memory."""
        # Load goals
        for data in self._load_jsonl(self.goals_file):
            goal = TargetGoal.from_dict(data)
            self._goals[goal.id] = goal
        
        # Load habits
        for data in self._load_jsonl(self.habits_file):
            habit = Habit.from_dict(data)
            self._habits[habit.id] = habit
        
        # Load experiments
        for data in self._load_jsonl(self.experiments_file):
            exp = Experiment.from_dict(data)
            self._experiments[exp.id] = exp
    
    def _save_goals(self):
        """Save all goals to JSONL."""
        entries = [g.to_dict() for g in self._goals.values()]
        self._rewrite_jsonl(self.goals_file, entries)
    
    def _save_habits(self):
        """Save all habits to JSONL."""
        entries = [h.to_dict() for h in self._habits.values()]
        self._rewrite_jsonl(self.habits_file, entries)
    
    def _save_experiments(self):
        """Save all experiments to JSONL."""
        entries = [e.to_dict() for e in self._experiments.values()]
        self._rewrite_jsonl(self.experiments_file, entries)
    
    # ==================== GOALS ====================
    
    def create_goal(self, title: str, description: str = "", 
                    target_date: Optional[str] = None) -> TargetGoal:
        """Create a new target goal."""
        goal = TargetGoal(
            title=title,
            description=description,
            target_date=target_date
        )
        self._goals[goal.id] = goal
        self._append_jsonl(self.goals_file, goal.to_dict())
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[TargetGoal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)
    
    def get_active_goals(self) -> List[TargetGoal]:
        """Get all active goals."""
        return [g for g in self._goals.values() if g.status == "active"]
    
    def update_goal(self, goal_id: str, **kwargs) -> Optional[TargetGoal]:
        """
        Update a goal's fields.
        Supports bidirectional updates from reflections.
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        
        for key, value in kwargs.items():
            if hasattr(goal, key):
                setattr(goal, key, value)
        
        goal.last_updated = datetime.now().isoformat()
        self._save_goals()
        return goal
    
    def add_habit_to_goal(self, goal_id: str, habit_id: str):
        """Link a habit to a goal."""
        goal = self._goals.get(goal_id)
        if goal and habit_id not in goal.habits:
            goal.habits.append(habit_id)
            goal.last_updated = datetime.now().isoformat()
            self._save_goals()
    
    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal and all its habits."""
        if goal_id not in self._goals:
            return False
        
        # Delete all habits for this goal
        habits_to_delete = [h.id for h in self.get_habits_for_goal(goal_id)]
        for habit_id in habits_to_delete:
            self.delete_habit(habit_id)
        
        # Delete the goal
        del self._goals[goal_id]
        self._save_goals()
        return True
    
    # ==================== HABITS ====================
    
    def create_habit(self, title: str, description: str = "",
                     goal_id: Optional[str] = None,
                     components: Optional[List[str]] = None) -> Habit:
        """Create a new habit, optionally linked to a goal."""
        habit = Habit(
            title=title,
            description=description,
            goal_id=goal_id,
            components=components or []
        )
        self._habits[habit.id] = habit
        self._append_jsonl(self.habits_file, habit.to_dict())
        
        # Link to goal if specified
        if goal_id:
            self.add_habit_to_goal(goal_id, habit.id)
        
        return habit
    
    def get_habit(self, habit_id: str) -> Optional[Habit]:
        """Get a habit by ID."""
        return self._habits.get(habit_id)
    
    def get_habits_for_goal(self, goal_id: str) -> List[Habit]:
        """Get all habits linked to a goal."""
        return [h for h in self._habits.values() if h.goal_id == goal_id]
    
    def get_active_habits(self) -> List[Habit]:
        """Get habits that are being developed."""
        return [h for h in self._habits.values() if h.status == "developing"]
    
    def update_habit(self, habit_id: str, **kwargs) -> Optional[Habit]:
        """
        Update a habit's fields.
        Supports bidirectional updates from reflections.
        """
        habit = self._habits.get(habit_id)
        if not habit:
            return None
        
        for key, value in kwargs.items():
            if hasattr(habit, key):
                setattr(habit, key, value)
        
        habit.last_updated = datetime.now().isoformat()
        self._save_habits()
        return habit
    
    def add_experiment_to_habit(self, habit_id: str, experiment_id: str):
        """Link an experiment to a habit."""
        habit = self._habits.get(habit_id)
        if habit and experiment_id not in habit.experiments:
            habit.experiments.append(experiment_id)
            habit.last_updated = datetime.now().isoformat()
            self._save_habits()
    
    def delete_habit(self, habit_id: str) -> bool:
        """Delete a habit."""
        if habit_id not in self._habits:
            return False
        
        habit = self._habits[habit_id]
        
        # Remove from parent goal's habit list
        if habit.goal_id and habit.goal_id in self._goals:
            goal = self._goals[habit.goal_id]
            if habit_id in goal.habits:
                goal.habits.remove(habit_id)
                self._save_goals()
        
        # Delete the habit
        del self._habits[habit_id]
        self._save_habits()
        return True
    
    # ==================== EXPERIMENTS ====================
    
    def create_experiment(self, title: str, description: str = "",
                          success_criteria: str = "",
                          habit_id: Optional[str] = None,
                          related_graph_nodes: Optional[List[str]] = None) -> Experiment:
        """Create a new experiment, optionally linked to a habit."""
        exp = Experiment(
            title=title,
            description=description,
            success_criteria=success_criteria,
            habit_id=habit_id,
            related_graph_nodes=related_graph_nodes or []
        )
        self._experiments[exp.id] = exp
        self._append_jsonl(self.experiments_file, exp.to_dict())
        
        # Link to habit if specified
        if habit_id:
            self.add_experiment_to_habit(habit_id, exp.id)
        
        return exp
    
    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        """Get an experiment by ID."""
        return self._experiments.get(exp_id)
    
    def get_experiments_for_habit(self, habit_id: str) -> List[Experiment]:
        """Get all experiments linked to a habit."""
        return [e for e in self._experiments.values() if e.habit_id == habit_id]
    
    def get_active_experiments(self) -> List[Experiment]:
        """Get experiments that are active or testing."""
        return [e for e in self._experiments.values() 
                if e.status in ("active", "testing")]
    
    def get_experiments_needing_followup(self) -> List[Experiment]:
        """
        Get experiments that need follow-up.
        Returns active experiments where today > last_checked (date-based).
        """
        today = date.today()
        needs_followup = []
        
        for exp in self.get_active_experiments():
            try:
                last_checked = date.fromisoformat(exp.last_checked)
                if today > last_checked:
                    needs_followup.append(exp)
            except (ValueError, TypeError):
                # If date parsing fails, include it
                needs_followup.append(exp)
        
        return needs_followup
    
    def log_progress(self, exp_id: str, outcome: str, notes: str,
                     marginal_gain_score: int) -> Optional[Experiment]:
        """
        Log a progress entry for an experiment.
        Supports multi-step logging within a session.
        
        Args:
            exp_id: Experiment ID
            outcome: "success" | "partial" | "not_tried" | "failed"
            notes: Description of what happened
            marginal_gain_score: -3 to +3 scale
        """
        exp = self._experiments.get(exp_id)
        if not exp:
            return None
        
        # Clamp score to valid range
        score = max(-3, min(3, marginal_gain_score))
        
        entry = ProgressEntry(
            date=date.today().isoformat(),
            outcome=outcome,
            notes=notes,
            marginal_gain_score=score
        )
        
        exp.progress_log.append(entry)
        exp.last_checked = date.today().isoformat()
        
        # Check if experiment should be completed (7+ successful days)
        if exp.successful_days() >= 7 and exp.status == "active":
            exp.status = "completed"
        
        self._save_experiments()
        return exp
    
    def complete_experiment(self, exp_id: str, 
                            reason: str = "completed") -> Optional[Experiment]:
        """Explicitly complete or abandon an experiment."""
        exp = self._experiments.get(exp_id)
        if not exp:
            return None
        
        exp.status = reason  # "completed" or "abandoned"
        self._save_experiments()
        return exp
    
    def update_experiment(self, exp_id: str, **kwargs) -> Optional[Experiment]:
        """Update an experiment's fields."""
        exp = self._experiments.get(exp_id)
        if not exp:
            return None
        
        # Handle log_entry specifically
        if 'log_entry' in kwargs:
            entry_data = kwargs.pop('log_entry')
            from tracking_schema import ProgressEntry
            # Check if it's a dict or object
            if isinstance(entry_data, dict):
                new_entry = ProgressEntry.from_dict(entry_data)
            else:
                new_entry = entry_data
            exp.progress_log.append(new_entry)

        for key, value in kwargs.items():
            if hasattr(exp, key) and key not in ('id', 'progress_log'):
                setattr(exp, key, value)
        
        self._save_experiments()
        return exp
    
    # ==================== ANALYSIS ====================
    
    def calculate_marginal_gains(self, exp_id: str) -> Dict[str, Any]:
        """Calculate marginal gains summary for an experiment."""
        exp = self._experiments.get(exp_id)
        if not exp:
            return {}
        
        total = exp.cumulative_progress()
        days = len(exp.progress_log)
        successful = exp.successful_days()
        
        return {
            "experiment_id": exp_id,
            "title": exp.title,
            "total_progress": total,
            "days_tracked": days,
            "successful_days": successful,
            "average_gain": total / days if days > 0 else 0,
            "status": exp.status,
            "near_completion": successful >= 5  # 5+ days = getting close
        }
    
    def get_overall_progress_summary(self) -> str:
        """Generate a natural language summary of overall progress."""
        active_goals = self.get_active_goals()
        active_habits = self.get_active_habits()
        active_experiments = self.get_active_experiments()
        needs_followup = self.get_experiments_needing_followup()
        
        lines = []
        
        if active_goals:
            lines.append(f"Active goals: {len(active_goals)}")
            for g in active_goals[:2]:
                lines.append(f"  - {g.title}")
        
        if active_habits:
            lines.append(f"Habits in development: {len(active_habits)}")
            for h in active_habits[:3]:
                lines.append(f"  - {h.title}")
        
        if needs_followup:
            lines.append(f"Experiments needing follow-up: {len(needs_followup)}")
            for e in needs_followup:
                progress = e.cumulative_progress()
                lines.append(f"  - {e.title} (progress: {'+' if progress >= 0 else ''}{progress})")
        
        return "\n".join(lines) if lines else "No active tracking items."


# --- INLINE TESTS ---
if __name__ == "__main__":
    import sys
    import shutil
    
    if "--test" in sys.argv:
        print("Running tracking_manager tests...")
        
        # Create isolated test directory
        test_dir = os.path.join(os.path.dirname(__file__), "tests", "output")
        os.makedirs(test_dir, exist_ok=True)
        
        # Clean up any previous test files
        for f in ["goals.jsonl", "habits.jsonl", "experiments.jsonl"]:
            path = os.path.join(test_dir, f)
            if os.path.exists(path):
                os.remove(path)
        
        # Initialize manager with test directory
        tm = TrackingManager(base_dir=test_dir)
        
        # Test goal creation
        goal = tm.create_goal(
            title="Emotionally regulated person",
            description="Someone who responds thoughtfully to triggers",
            target_date="2025-06-14"
        )
        assert goal.id.startswith("goal_"), "Goal ID format wrong"
        assert len(tm.get_active_goals()) == 1, "Goal not tracked"
        print("  ✓ Goal creation")
        
        # Test habit creation linked to goal
        habit = tm.create_habit(
            title="Recognize overload",
            description="Notice when entering emotional overload",
            goal_id=goal.id,
            components=["Body awareness", "Emotion naming"]
        )
        assert habit.goal_id == goal.id, "Habit not linked to goal"
        goal_updated = tm.get_goal(goal.id)
        assert habit.id in goal_updated.habits, "Habit not added to goal"
        print("  ✓ Habit creation and goal linking")
        
        # Test experiment creation linked to habit
        exp = tm.create_experiment(
            title="4-7-8 breathing",
            description="Breathing technique for calm",
            success_criteria="Feel calmer after 90 seconds",
            habit_id=habit.id
        )
        assert exp.habit_id == habit.id, "Experiment not linked to habit"
        habit_updated = tm.get_habit(habit.id)
        assert exp.id in habit_updated.experiments, "Experiment not added to habit"
        print("  ✓ Experiment creation and habit linking")
        
        # Test progress logging
        tm.log_progress(exp.id, "partial", "Tried it, felt somewhat calmer", 1)
        tm.log_progress(exp.id, "success", "Worked well today", 2)
        exp_updated = tm.get_experiment(exp.id)
        assert exp_updated.cumulative_progress() == 3, "Progress calculation wrong"
        assert exp_updated.successful_days() == 2, "Successful days wrong"
        print("  ✓ Progress logging and calculations")
        
        # Test follow-up detection
        exp_updated.last_checked = "2025-12-01"  # Set to past date
        tm._save_experiments()
        needs_followup = tm.get_experiments_needing_followup()
        assert len(needs_followup) == 1, "Follow-up detection failed"
        print("  ✓ Follow-up detection")
        
        # Test bidirectional update (update goal from reflection)
        tm.update_goal(goal.id, description="Updated based on reflection insights")
        goal_refreshed = tm.get_goal(goal.id)
        assert "Updated" in goal_refreshed.description, "Bidirectional update failed"
        print("  ✓ Bidirectional goal update")
        
        # Test persistence (reload from files)
        tm2 = TrackingManager(base_dir=test_dir)
        assert len(tm2.get_active_goals()) == 1, "Goals not persisted"
        assert len(tm2.get_active_habits()) == 1, "Habits not persisted"
        assert len(tm2.get_active_experiments()) == 1, "Experiments not persisted"
        print("  ✓ JSONL persistence")
        
        # Test marginal gains calculation
        gains = tm.calculate_marginal_gains(exp.id)
        assert gains["total_progress"] == 3, "Marginal gains calculation wrong"
        print("  ✓ Marginal gains analysis")
        
        # Test overall progress summary
        summary = tm.get_overall_progress_summary()
        assert "Emotionally regulated" in summary, "Summary missing goal"
        print("  ✓ Overall progress summary")
        
        print("\nAll tracking_manager tests passed! ✓")
    else:
        print("Usage: python tracking_manager.py --test")
