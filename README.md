# Reflection Coach

An LLM-powered daily reflection system with experiment tracking and knowledge graph integration.

## Installation

```bash
pip install -r requirements.txt
```

Create a `.env` file with your API key:
```
DEEPSEEK_API_KEY=your_key_here
```

## Quick Start

```bash
python LLM_reflection.py
```

## Features

- **Kolb Cycle Reflections**: Structured daily reflections following the experiential learning cycle
- **Experiment Tracking**: Create, monitor, and log micro-experiments for habit development
- **Knowledge Graph**: Persistent graph of beliefs, emotions, and insights extracted from sessions
- **Marginal Gains**: Track cumulative progress on experiments with -3 to +3 scoring

## Project Structure

```
├── LLM_reflection.py         # Main entry point
├── src/                      # Core modules
│   ├── tracking_manager.py   # Goals/Habits/Experiments CRUD
│   ├── graph_manager.py      # Knowledge graph operations
│   ├── context_manager.py    # Session context builder
│   └── skill_loader.py       # YAML behavior loader
├── scripts/                  # CLI tools
│   └── experiment_manager.py # Experiment management CLI
├── skills/                   # YAML behavior definitions
└── data/                     # Persistent state (local)
```

## License

MIT
