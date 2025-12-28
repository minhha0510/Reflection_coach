"""
Skill Loader for YAML-based agent behavior definitions.

Loads skill definitions from skills/ directory and provides:
- Stage-aware prompt selection
- Grounding technique detection
- Experiment guardrails
"""

import os
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SkillConfig:
    """Loaded configuration from a YAML skill file."""
    name: str
    raw: Dict[str, Any]
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        return self.raw[key]


class SkillLoader:
    """Loads and manages YAML skill definitions."""
    
    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self._cache: Dict[str, SkillConfig] = {}
        self._load_all_skills()
    
    def _load_all_skills(self):
        """Recursively load all YAML files in skills directory."""
        if not os.path.exists(self.skills_dir):
            print(f"[SkillLoader] Warning: skills directory not found at {self.skills_dir}")
            return
            
        for root, dirs, files in os.walk(self.skills_dir):
            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, self.skills_dir)
                    key = rel_path.replace(os.sep, '/').replace('.yaml', '').replace('.yml', '')
                    self._load_skill(key, path)
    
    def _load_skill(self, key: str, path: str):
        """Load a single skill file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data:
                self._cache[key] = SkillConfig(
                    name=data.get('name', key),
                    raw=data
                )
        except Exception as e:
            print(f"[SkillLoader] Error loading {path}: {e}")
    
    def get_skill(self, key: str) -> Optional[SkillConfig]:
        """Get a loaded skill by key (e.g., 'reflection/stages/grounding')."""
        return self._cache.get(key)
    
    def list_skills(self) -> List[str]:
        """List all loaded skill keys."""
        return list(self._cache.keys())
    
    # --- Convenience Methods for Reflection System ---
    
    def get_grounding_config(self) -> Optional[SkillConfig]:
        """Get the mandatory grounding configuration."""
        return self.get_skill('reflection/stages/grounding')
    
    def get_stage_config(self, stage: str) -> Optional[SkillConfig]:
        """Get config for a specific Kolb stage."""
        return self.get_skill(f'reflection/stages/{stage}')
    
    def get_experiment_guard(self) -> Optional[SkillConfig]:
        """Get experiment guardrails config."""
        return self.get_skill('reflection/experiment_guard')
    
    def get_daily_flow(self) -> Optional[SkillConfig]:
        """Get main daily flow orchestration."""
        return self.get_skill('reflection/daily_flow')
    
    def check_physical_sensation_triggers(self, text: str) -> bool:
        """Check if text contains physical sensation triggers that warrant grounding offer."""
        observation = self.get_stage_config('observation')
        if not observation:
            return False
        
        triggers = observation.get('physical_sensation_triggers', [])
        text_lower = text.lower()
        return any(trigger.lower() in text_lower for trigger in triggers)
    
    def check_experiment_readiness_signals(self, text: str) -> bool:
        """Check if user is signaling readiness for experiment."""
        guard = self.get_experiment_guard()
        if not guard:
            return False
        
        signals = guard.get('entry_signals', [])
        text_lower = text.lower()
        return any(signal.lower() in text_lower for signal in signals)
    
    def get_experiment_limit_message(self, active_count: int, experiments: List[Any] = None) -> Optional[str]:
        """Get appropriate message based on active experiment count."""
        guard = self.get_experiment_guard()
        if not guard:
            return None
        
        max_active = guard.get('max_active_experiments', 2)
        
        if active_count < max_active:
            return None  # Under limit, no message needed
        elif active_count == max_active:
            return guard.get('on_at_limit', {}).get('message', '')
        else:
            msg = guard.get('on_over_limit', {}).get('message', '')
            return msg.format(count=active_count) if msg else None
    
    def build_stage_prompt_context(self, stage: str) -> str:
        """Build prompt context for a specific stage."""
        config = self.get_stage_config(stage)
        if not config:
            return ""
        
        parts = []
        
        # Add rules if present
        rules = config.get('rules', [])
        if rules:
            parts.append("RULES FOR THIS STAGE:")
            for rule in rules:
                parts.append(f"- {rule}")
        
        # Add prohibited patterns if present (for abstraction)
        prohibited = config.get('prohibited_patterns', [])
        if prohibited:
            parts.append("\nDO NOT:")
            for p in prohibited:
                parts.append(f"- {p}")
        
        return "\n".join(parts)


# --- Test Helper ---
def test_skill_loader():
    """Quick test of skill loader functionality."""
    import sys
    
    # Get skills directory relative to this file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.join(script_dir, "skills")
    
    loader = SkillLoader(skills_dir)
    
    print("=== Skill Loader Test ===\n")
    print(f"Skills directory: {skills_dir}")
    print(f"Loaded skills: {loader.list_skills()}\n")
    
    # Test grounding config
    grounding = loader.get_grounding_config()
    if grounding:
        print(f"✓ Grounding config loaded: {grounding.name}")
        print(f"  Mandatory: {grounding.get('mandatory', False)}")
    else:
        print("✗ Grounding config not found")
    
    # Test experiment guard
    guard = loader.get_experiment_guard()
    if guard:
        print(f"✓ Experiment guard loaded: {guard.name}")
        print(f"  Max active: {guard.get('max_active_experiments', 'N/A')}")
    else:
        print("✗ Experiment guard not found")
    
    # Test trigger detection
    test_texts = [
        "I felt tension in my stomach",
        "I was just thinking about work",
        "I want to try something different",
    ]
    
    print("\n--- Trigger Detection ---")
    for text in test_texts:
        physical = loader.check_physical_sensation_triggers(text)
        experiment = loader.check_experiment_readiness_signals(text)
        print(f"'{text[:40]}...'")
        print(f"  Physical sensation: {physical}")
        print(f"  Experiment ready: {experiment}")
    
    # Test limit messages
    print("\n--- Experiment Limit Messages ---")
    for count in [1, 2, 5]:
        msg = loader.get_experiment_limit_message(count)
        print(f"Count {count}: {msg[:60] if msg else 'No message'}...")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_skill_loader()
