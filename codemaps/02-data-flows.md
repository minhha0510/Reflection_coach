# Codemap: Reflections Data Flows (auto-maintained by LLM)
Last updated: 2025-11-20
Responsibility: Major data / request / event flows through the system

## 1. Graph-Enhanced Cognitive Cycle (Daily Reflection)
```mermaid
graph TD;
    User[User Input] --> Retrieval[Ego Walk];
    GraphDB[(reflection_graph.json)] -- Query Anchors --> Retrieval;
    Retrieval -- Context String --> LLM[Guidance Engine];
    
    LLM -- Probing Question --> User;
    User --> Ingest[IngestionPipeline];
    Ingest -- Extract Nodes/Edges --> GraphMgr[GraphManager];
    GraphMgr -- Update State --> GraphDB;
    LLM -- Final Summary --> Markdown[Daily Log];
```

## 2. Weekly Review Flow
```mermaid
graph TD
    User[User Selects Weekly] --> App[LLM_reflection.py]
    App -->|Read Last 7 Days| DailyDir[daily/*.md]
    App -->|Load Previous Context| ContextFile[weekly/context_memory.json]
    DailyDir -->|Content| App
    ContextFile -->|Context| App
    
    User -->|Answer| Input[User Input]
    Input --> GraphQuery[Ego Walk]
    GraphDB[(reflection_graph.json)] --> GraphQuery
    GraphQuery -->|Graph Context| Prompt[Context + Prompt]
    
    App -->|Aggregate| Prompt
    Prompt -->|Question| LLM[DeepSeek API]
    LLM -->|Insightful Question| User
    User -->|'quit'| Summary[Generate Summary]
    Summary -->|Save| ContextFile
    Summary -->|Save Conversation| WeeklyFile[weekly/Weekly-Review-YYYY-MM-DD.md]
```
