# Codemap: Common Patterns and Rules (auto-maintained by LLM)
Last updated: 2025-11-20
Responsibility: Architectural decisions, coding standards, anti-patterns to avoid, landmines

## 1. LLM Integration Patterns

### JSON Response Handling
**ALWAYS** strip markdown before parsing JSON from LLM:
```python
def _strip_markdown_json(text):
    """Strip markdown code blocks from JSON responses"""
    text = text.strip()
    if text.startswith('```'):
        first_newline = text.find('\n')
        last_backticks = text.rfind('```')
        if first_newline != -1 and last_backticks != -1:
            text = text[first_newline+1:last_backticks].strip()
    return text

# Usage
raw_response = llm_call(...)
clean_json = _strip_markdown_json(raw_response)
data = json.loads(clean_json)
```

### API Timeouts
*   **Standard calls**: 120 seconds minimum
*   **Reason**: Batch ingestion can take 60+ seconds for long conversations
*   **Location**: All `requests.post()` calls to DeepSeek API

## 2. Graph Management

### Ingestion Timing
**RULE**: Ingest graph data **after** the session ends, not during.
*   **Why**: Real-time ingestion caused slowdowns (30s+ per turn) and added latency to user experience
*   **Implementation**: Call `ingestion_pipeline.process_session(full_text)` after saving the markdown file

### Node Creation
*   Always use dataclasses from `graph_schema.py`
*   Never create nodes with raw dictionaries
*   Import `Node` base class when handling generic Person nodes

## 3. Error Handling

### Summary Generation Failures
**CRITICAL**: Always handle LLM summary parsing failures gracefully.

```python
try:
    summary_clean = self._strip_markdown_json(summary_raw)
    data = json.loads(summary_clean)
    self.save_daily_entry(data, full_text)
except:
    print("Error parsing summary JSON. Saving raw text.")
    self.save_daily_entry({}, full_text)  # Empty dict as fallback
```

*   **Pattern**: Wrap JSON parsing in try/except
*   **Fallback**: Pass empty dict `{}` to save function rather than crashing
*   **Why**: Preserves the full conversation even if summary extraction fails
*   **Location**: `run_daily_reflection()` and `run_weekly_review()`

## 4. File Structure

### Import Organization
Standard import order:
1. Standard library (`os`, `json`, `datetime`)
2. Third-party (`requests`, `networkx`, `prompt_toolkit`)
3. Local modules (`graph_manager`, `ingestion_pipeline`)

### Prompt Toolkit Module Path
**LANDMINE**: Use `prompt_toolkit.key_binding` (singular) not `key_bindings` (plural)
*   Version 3.0.43 uses singular form
*   This broke in production - keep tests for this

## 5. Data Persistence

### Graph Persistence
*   Graph auto-saves after every ingestion
*   File: `reflection_graph.json`
*   Format: NetworkX node-link JSON format
*   **Do NOT** commit to git (in `.gitignore`)

### Weekly Context Memory
*   File: `weekly/context_memory.json`
*   Purpose: Progressive learning between weekly reviews
*   Contains: week_theme, major_wins, struggles, key_takeaway, focus_for_next_week
*   Auto-created on first weekly review completion

### User Data Privacy
*   Daily/weekly reflections contain personal data
*   **Always** exclude from git via `.gitignore`
*   Test files blocked: `test_*.py`, `verify_*.py`, `prototype_*.py`, `backfill_*.py`

## 6. Graph Context Integration

### Ego Walk in Both Flows
**RULE**: Weekly reviews now use graph context, same as daily reflections.

```python
# In both run_daily_reflection() and run_weekly_review():
anchors = self.graph_manager.find_nodes_by_text(user_input)
anchor_ids = [n['id'] for n in anchors]
graph_context = self.graph_manager.ego_walk(anchor_ids[:3]) if anchor_ids else "No specific past patterns found."
```

*   **Daily**: Graph context injected into `DAILY_SYSTEM_PROMPT`
*   **Weekly**: Graph context injected into `WEEKLY_SYSTEM_PROMPT` (added 2025-11-22)
*   **Why**: Provides historical pattern awareness across all reflections, not just recent ones

## 7. Visualization

### Generating Graph HTML
```bash
python visualize_graph.py
```
*   Reads: `reflection_graph.json`
*   Generates: `reflection_graph.html` (Vis.js interactive graph)
*   Color scheme: Belief (Gold), Event (Green), Emotion (Pink), Person (Salmon)
*   Opens automatically in default browser
