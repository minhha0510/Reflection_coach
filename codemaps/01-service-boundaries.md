# Codemap: Service Boundaries (auto-maintained by LLM)
Last updated: 2025-11-20
Responsibility: Every service / module, what it owns, what it must never touch, public contracts

## Module Boundaries

### 1. Core Application (`LLM_reflection.py`)
*   **Owns**:
    *   Application lifecycle (Main Menu, Loop).
    *   User Input/Output (CLI interactions).
    *   Orchestration: Calls `GraphManager` for context and `IngestionPipeline` for updates.
    *   API Client (`call_llm`): Handles authentication, retries, and error parsing.
*   **Contracts**:
    *   Requires `DEEPSEEK_API_KEY` env var.
    *   Expects `reflection_graph.json` to be managed by `GraphManager`.

### 2. Graph State Manager (`graph_manager.py`)
*   **Owns**:
    *   The "Psyche Graph" (NetworkX DiGraph).
    *   Persistence: Loading/Saving `reflection_graph.json`.
    *   Retrieval Logic: `ego_walk()` (Context Stuffing).
    *   Query Logic: `find_nodes_by_text()`.
*   **Must Never**:
    *   Directly call the LLM (separation of concerns).
    *   Handle UI/CLI logic.

### 3. Ingestion Pipeline (`ingestion_pipeline.py`)
*   **Owns**:
    *   LLM Interaction for *Extraction* (System Prompt: `EXTRACTION_SYSTEM_PROMPT`).
    *   Parsing raw text into `Node` and `Edge` objects.
    *   Writing to `GraphManager`.
*   **Contracts**:
    *   Input: Raw user text string.
    *   Output: Updates to the Graph.

### 4. Data Schema (`Kolb_template.json` & `graph_schema.py`)
*   **Owns**:
    *   `Kolb_template.json`: Structure of Kolb's Learning Cycle.
    *   `graph_schema.py`: Strict Ontology for Nodes (`User`, `Belief`, `Event`) and Edges (`TRIGGERED`, `CONTRADICTS`).
*   **Must Never**:
    *   Contain runtime logic.

### 3. Storage Directories (`daily/`, `weekly/`)
*   **Owns**:
    *   Persistence of user reflections.
*   **Rules**:
    *   `daily/`: Files named `YYYY-MM-DD-HHMMSS.md`. Contains structured YAML frontmatter + raw conversation.
    *   `weekly/`: Files named `Weekly-Review-YYYY-MM-DD.md`. Contains aggregated context + review conversation.
    *   `weekly/context_memory.json`: Persistent memory of weekly summaries for progressive learning.

### 4. Visualization Module (`visualize_graph.py`)
*   **Owns**:
    *   Reading `reflection_graph.json`.
    *   Generating `reflection_graph.html` with Vis.js interactive visualization.
*   **Must Never**:
    *   Modify the graph data.
    *   Require runtime user interaction (runs as standalone script).

### 5. External Services
*   **DeepSeek API**:
    *   **Role**: Intelligence provider for conversation and summarization.
    *   **Contract**: JSON-RPC style chat completions.
    *   **Failure Handling**: Application must handle timeouts and 5xx errors gracefully (implemented in `call_llm`).
