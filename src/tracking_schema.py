"""
Hierarchical Tracking Schema for Reflections
=============================================
Defines data structures for:
- Target Goals (6-12 month vision)
- Habits (skills to develop)
- Experiments (daily micro-tests)
- Progress Entries (marginal gains log)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class ProgressEntry:
    """A single progress log entry for an experiment."""
    date: str
    outcome: str  # "success" | "partial" | "not_tried" | "failed"
    notes: str
    marginal_gain_score: int  # -3 to +3 scale
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "outcome": self.outcome,
            "notes": self.notes,
            "marginal_gain_score": self.marginal_gain_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressEntry":
        return cls(
            date=data["date"],
            outcome=data["outcome"],
            notes=data["notes"],
            marginal_gain_score=data["marginal_gain_score"]
        )


@dataclass
class Experiment:
    """
    A micro-test for habit development.
    Experiments are daily/weekly tests that build toward habits.
    """
    id: str = field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    habit_id: Optional[str] = None  # Parent habit (can be None initially)
    title: str = ""
    description: str = ""
    success_criteria: str = ""
    status: str = "active"  # "active" | "testing" | "completed" | "abandoned"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checked: str = field(default_factory=lambda: datetime.now().date().isoformat())
    related_graph_nodes: List[str] = field(default_factory=list)
    progress_log: List[ProgressEntry] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "habit_id": self.habit_id,
            "title": self.title,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "status": self.status,
            "created_at": self.created_at,
            "last_checked": self.last_checked,
            "related_graph_nodes": self.related_graph_nodes,
            "progress_log": [p.to_dict() for p in self.progress_log],
            "embedding": self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experiment":
        progress_log = [ProgressEntry.from_dict(p) for p in data.get("progress_log", [])]
        return cls(
            id=data["id"],
            habit_id=data.get("habit_id"),
            title=data["title"],
            description=data["description"],
            success_criteria=data.get("success_criteria", ""),
            status=data.get("status", "active"),
            created_at=data["created_at"],
            last_checked=data.get("last_checked", datetime.now().date().isoformat()),
            related_graph_nodes=data.get("related_graph_nodes", []),
            progress_log=progress_log,
            embedding=data.get("embedding")
        )
    
    def cumulative_progress(self) -> int:
        """Calculate total marginal gains (-3 to +3 per entry, accumulates)."""
        return sum(p.marginal_gain_score for p in self.progress_log)
    
    def successful_days(self) -> int:
        """Count days with positive outcome."""
        return len([p for p in self.progress_log if p.outcome in ("success", "partial")])


@dataclass
class Habit:
    """
    A skill or behavior pattern to develop.
    Habits are linked to goals and contain experiments.
    Can be updated/refined through daily reflections.
    """
    id: str = field(default_factory=lambda: f"hab_{uuid.uuid4().hex[:8]}")
    goal_id: Optional[str] = None  # Parent goal
    title: str = ""
    description: str = ""
    components: List[str] = field(default_factory=list)  # Sub-skills to develop
    experiments: List[str] = field(default_factory=list)  # IDs of experiments
    status: str = "developing"  # "developing" | "established" | "maintained"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "components": self.components,
            "experiments": self.experiments,
            "status": self.status,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "embedding": self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Habit":
        return cls(
            id=data["id"],
            goal_id=data.get("goal_id"),
            title=data["title"],
            description=data.get("description", ""),
            components=data.get("components", []),
            experiments=data.get("experiments", []),
            status=data.get("status", "developing"),
            created_at=data["created_at"],
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            embedding=data.get("embedding")
        )


@dataclass
class TargetGoal:
    """
    A 6-12 month vision of who you want to become.
    Goals are broken down into habits needed for that lifestyle.
    Can be refined based on reflection insights.
    """
    id: str = field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:8]}")
    title: str = ""  # "Emotionally regulated person"
    description: str = ""  # What this person looks like
    target_date: Optional[str] = None  # 6-12 months out
    habits: List[str] = field(default_factory=list)  # IDs of associated habits
    status: str = "active"  # "active" | "achieved" | "revised"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_date": self.target_date,
            "habits": self.habits,
            "status": self.status,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "embedding": self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetGoal":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            target_date=data.get("target_date"),
            habits=data.get("habits", []),
            status=data.get("status", "active"),
            created_at=data["created_at"],
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            embedding=data.get("embedding")
        )


# --- INLINE TESTS ---
if __name__ == "__main__":
    import sys
    import os
    
    if "--test" in sys.argv:
        print("Running tracking_schema tests...")
        
        # Create test output directory
        test_dir = os.path.join(os.path.dirname(__file__), "tests", "output")
        os.makedirs(test_dir, exist_ok=True)
        
        # Test ProgressEntry
        entry = ProgressEntry(
            date="2025-12-14",
            outcome="partial",
            notes="Tried the breathing, felt calmer",
            marginal_gain_score=1
        )
        entry_dict = entry.to_dict()
        entry_restored = ProgressEntry.from_dict(entry_dict)
        assert entry_restored.marginal_gain_score == 1, "ProgressEntry serialization failed"
        print("  ✓ ProgressEntry serialization")
        
        # Test Experiment
        exp = Experiment(
            title="4-7-8 breathing + anchor song",
            description="Breathing technique combined with calming music",
            success_criteria="Feel calmer after 90 seconds",
            habit_id="hab_001"
        )
        exp.progress_log.append(entry)
        exp_dict = exp.to_dict()
        exp_restored = Experiment.from_dict(exp_dict)
        assert exp_restored.cumulative_progress() == 1, "Experiment progress calc failed"
        assert exp_restored.successful_days() == 1, "Experiment days calc failed"
        print("  ✓ Experiment serialization and calculations")
        
        # Test Habit
        habit = Habit(
            title="Recognize overload and name needs",
            description="Ability to notice when entering emotional overload",
            components=["Body awareness", "Emotion naming", "Need identification"],
            goal_id="goal_001"
        )
        habit.experiments.append(exp.id)
        habit_dict = habit.to_dict()
        habit_restored = Habit.from_dict(habit_dict)
        assert len(habit_restored.experiments) == 1, "Habit experiments tracking failed"
        print("  ✓ Habit serialization")
        
        # Test TargetGoal
        goal = TargetGoal(
            title="Emotionally regulated person",
            description="Someone who responds thoughtfully to triggers",
            target_date="2025-06-14"
        )
        goal.habits.append(habit.id)
        goal_dict = goal.to_dict()
        goal_restored = TargetGoal.from_dict(goal_dict)
        assert len(goal_restored.habits) == 1, "Goal habits tracking failed"
        print("  ✓ TargetGoal serialization")
        
        print("\nAll tracking_schema tests passed! ✓")
    else:
        print("Usage: python tracking_schema.py --test")
