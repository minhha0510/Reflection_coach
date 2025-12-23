# Codemap: Knowledge Graph Schema (auto-maintained by LLM)
Last updated: 2025-11-22
Responsibility: Defines the ontology and reproduction steps for the Psyche Graph.

## 1. Core Ontology
The graph uses a strict ontology defined in `graph_schema.py`.

### Node Types
*   **User**: The central subject.
*   **Belief**: A core conviction or schema (e.g., "I am not good enough").
*   **Event**: A specific occurrence (e.g., "Failed math test").
*   **Emotion**: A feeling state (e.g., "Anxiety", "Joy").
*   **Topic**: A general subject (e.g., "Career", "Family").
*   **Utterance**: A raw quote from the user.
*   **Distortion**: A cognitive distortion (e.g., "All-or-nothing thinking").

### Edge Types
*   **EXPERIENCED**: User -> Event/Emotion
*   **HAS_BELIEF**: User -> Belief
*   **TRIGGERED**: Event -> Emotion/Belief
*   **INTERPRETED_AS**: Event -> Belief
*   **REINFORCES**: Event/Belief -> Belief
*   **CONTRADICTS**: Event/Belief -> Belief
*   **MENTIONS**: Utterance -> Any Node

## 2. Graph Reproduction
If `reflection_graph.json` is lost, the graph can be rebuilt from the raw Markdown logs in `daily/`.

### Reproduction Algorithm
1.  **Initialize**: Create a fresh `GraphManager`.
2.  **Iterate**: Loop through all `.md` files in `daily/`.
3.  **Extract**: Parse the "Full Conversation" section of each file.
4.  **Ingest**: Pass each user turn to `IngestionPipeline.process_interaction()`.
    *   *Note*: This will re-trigger LLM extraction for every historical entry.
5.  **Save**: Call `GraphManager.save_graph()`.

### Recovery Script Snippet
```python
from graph_manager import GraphManager
from ingestion_pipeline import IngestionPipeline
import os

gm = GraphManager("recovered_graph.json")
pipe = IngestionPipeline(gm)

for filename in os.listdir("daily"):
    if filename.endswith(".md"):
        with open(f"daily/{filename}") as f:
            content = f.read()
            # Extract user parts from content...
            # pipe.process_interaction(user_text)

gm.save_graph()
```
