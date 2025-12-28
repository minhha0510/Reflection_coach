---
description: Standard protocol for maintaining codebase context and memory
---

# GCC Codebase Manager Protocol

> **Note:** These commands assume the tool is installed in `.agent/codebase_manager`. If installed elsewhere, adjust the paths accordingly. The tools assume they are run from the project root.


This workflow defines the standard operating procedure for maintaining the agent's cognitive state and codebase understanding using the GCC (Git-Context-Controller) tools.

**ALL agents must follow the "End of Session Protocol" before finishing their turn.**

## 1. Start of Session (Context Loading)

At the beginning of a session, check the current cognitive state and codebase overview.

```bash
# Check current cognitive state (goals, open loops, branch)
python3 .agent/codebase_manager/gcc_controller.py status

# Get a high-level map of the codebase structure
# (Output is formatted for LLM context)
python3 .agent/codebase_manager/repo_map_generator.py
```

## 2. During Development (Impact Analysis)

Before modifying critical files, check for dependencies to avoid regressions.

```bash
# Check what files depend on the target file
# Example: python3 .agent/codebase_manager/dependency_analyzer.py --query graph_schema.py
python3 .agent/codebase_manager/dependency_analyzer.py --query <filename>
```

**Experimental Changes:**
If a change is risky/experimental, create a branch first.

```bash
# Create a new branch
python3 .agent/codebase_manager/gcc_controller.py branch "experiment/feature-name"

# ... do work ...

# If successful:
# python3 .agent/codebase_manager/gcc_controller.py commit "Success message"

# If failed:
# python3 .agent/codebase_manager/gcc_controller.py revert "main"
```

## 3. Handling Errors (Experience Reuse)

If you solve a tricky error, search for or record the solution.

**Search Past Solutions:**
```bash
# Find similar past problems
python3 .agent/codebase_manager/trajectory_cache.py find "Error message here"
```

**Record New Solution:**
```bash
# Add a successful trajectory for future agents
# Usage: add "<Trigger/Error>" "<Strategy used>" "<Outcome>"
python3 .agent/codebase_manager/trajectory_cache.py add "ImportError: No module named 'xyz'" "Run pip install xyz" "SUCCESS"
```

---

## 4. End of Session Protocol (MANDATORY)

**You MUST perform these steps before finishing the session if you made any code changes.**

### Step A: Regenerate Maps (If code structure changed)
If you added files, classes, functions, or changed imports:
```bash
# // turbo
python3 .agent/codebase_manager/repo_map_generator.py && python3 .agent/codebase_manager/dependency_analyzer.py
```

### Step B: Commit Cognitive State
Capture what was accomplished, what goals remain, and what the next agent should focus on.

```bash
# Usage: commit "<Summary of work done>"
python3 .agent/codebase_manager/gcc_controller.py commit "Implemented feature X. Next: Test feature Y."
```

### Step C: Verify Integrity
Ensure no "dirty" state files (like `gcc-temp` or `__pycache__`) are polluting the context maps. The regeneration step above (Step A) usually handles this, but verify visually if needed.

---

## File Locations Reference

-   **GCC State**: `.agent/codebase_manager/state/main.md`
-   **Repo Map**: `.agent/codebase_manager/state/repo_map.json`
-   **Dependency Graph**: `.agent/codebase_manager/state/dependency_graph.json`
-   **Trajectories**: `.agent/codebase_manager/state/trajectories.jsonl`