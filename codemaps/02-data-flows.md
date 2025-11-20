# Codemap: Reflections Data Flows (auto-maintained by LLM)
Last updated: 2025-11-20
Responsibility: Major data / request / event flows through the system

## 1. Graph-Enhanced Cognitive Cycle (Daily Reflection)
```mermaid
graph TD;
    User[User Input] --> Ingest[IngestionPipeline];
    Ingest -- Extract Nodes/Edges --> GraphMgr[GraphManager];
    GraphMgr -- Update State --> GraphDB[(reflection_graph.json)];
    
    User --> Retrieval[Ego Walk];
    GraphDB -- Query Anchors --> Retrieval;
    Retrieval -- Context String --> LLM[Guidance Engine];
    
    LLM -- Probing Question --> User;
    LLM -- Final Summary --> Markdown[Daily Log];
```

## 2. Weekly Review Flow
```mermaid
graph TD
    User[User Selects Weekly] --> App[LLM_reflection.py]
    App -->|Read Last 7 Days| DailyDir[daily/*.md]
    DailyDir -->|Content| App
    App -->|Context + Prompt| LLM[DeepSeek API]
    LLM -->|Insightful Question| App
    App -->|Display| User
    User -->|Answer| App
    App -->|Loop| LLM
    User -->|'quit'| App
    App -->|Save Conversation| WeeklyFile[weekly/Weekly-Review-YYYY-MM-DD.md]
```
