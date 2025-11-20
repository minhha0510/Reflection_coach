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
*   **Storage Layer**: 
    *   Graph: `reflection_graph.json` (NetworkX serialization).
    *   Files: `daily/` and `weekly/` (Markdown backups).
*   **Template System**: JSON-based configuration (`Kolb_template.json`) defining the reflection stages and prompts.

## Tech Stack
*   **Language**: Python 3.x
*   **LLM Provider**: DeepSeek API (`deepseek-chat`)
*   **Graph Engine**: NetworkX (In-memory graph), serialized to JSON.
*   **Dependencies**: `requests`, `prompt_toolkit`, `networkx`
*   **Data Format**: JSON (Graph & Templates), Markdown (Logs)

## Data Flow
1.  **Daily**: User Input -> **Ingestion Pipeline** (Extract Nodes) -> **Graph Manager** (Update State) -> **Ego Walk** (Retrieve Context) -> LLM Guidance Loop -> Final Summary -> Markdown File
2.  **Weekly**: Load last 7 days -> LLM Context -> Conversational Review -> Markdown File
