# Codemap: Reflections System Overview (auto-maintained by LLM)
Last updated: 2025-11-20
Responsibility: High-level architecture, main components, tech stack, deployment topology

## System Summary
A CLI-based cognitive habit reflector that guides users through Kolb's Learning Cycle using an LLM (DeepSeek) to deepen self-awareness and generate actionable marginal gains.

## Core Components
*   **CLI Interface**: Interactive command-line interface for daily reflections and weekly reviews.
*   **Guidance Engine**: LLM-driven persona (Coach/Psychoanalyst) that asks probing questions based on Kolb's cycle.
*   **Graph State Manager**: (`graph_manager.py`) Manages the "Psyche Graph" (NetworkX) for long-term context and evolution tracking.
*   **Ingestion Pipeline**: (`ingestion_pipeline.py`) Extracts structured nodes/edges from user text using LLM.
*   **Visualization Tool**: (`visualize_graph.py`) Generates interactive HTML visualization of the graph using Vis.js.
*   **Storage Layer**: 
    *   Graph: `reflection_graph.json` (NetworkX serialization).
    *   Files: `daily/` and `weekly/` (Markdown backups).
    *   Weekly Context: `weekly/context_memory.json` (Progressive learning state).
*   **Template System**: JSON-based configuration (`Kolb_template.json`) defining the reflection stages and prompts.

## Tech Stack
*   **Language**: Python 3.x
*   **LLM Provider**: DeepSeek API (`deepseek-chat`)
*   **Graph Engine**: NetworkX (In-memory graph), serialized to JSON.
*   **Visualization**: Vis.js (browser-based graph rendering)
*   **Dependencies**: `requests`, `prompt_toolkit`, `networkx`, `python-dotenv`
*   **Data Format**: JSON (Graph & Templates), Markdown (Logs)

## Data Flow
1.  **Daily**: User Input -> **Ego Walk** (Retrieve Graph Context) -> LLM Guidance Loop -> Final Summary -> **Ingestion Pipeline** (Batch Extract Nodes/Edges from full session) -> **Graph Manager** (Update State) -> Markdown File
2.  **Weekly**: Load last 7 days + Previous context -> User Input -> **Ego Walk** (Retrieve Graph Patterns) -> LLM Conversational Review -> Summary -> Save weekly context JSON
