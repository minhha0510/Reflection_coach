# Codemap: Reflections Dependencies (auto-maintained by LLM)
Last updated: 2025-11-20
Responsibility: Critical integration points, external services, databases, message brokers, caches

## 1. External Services
*   **DeepSeek API**
    *   **Criticality**: High. The application is a wrapper around this API.
    *   **Failure Impact**: Application cannot function (returns errors to user).
    *   **Config**: Expects `DEEPSEEK_API_KEY` env var.

## 2. File System Dependencies
*   **Template (`Kolb_template.json`)**
    *   **Role**: Schema definition for the reflection process.
    *   **Criticality**: Must exist in the same directory as the script.
    *   **Failure Impact**: Application exits immediately if missing or invalid JSON.

*   **Storage Directories (`daily/`, `weekly/`)**
    *   **Role**: Database.
    *   **Criticality**: Created automatically if missing, but write permissions are required.

## 3. LLM API Configuration
*   **Timeout Settings**
    *   **Current**: 120 seconds for all API calls (increased from 30s).
    *   **Reason**: Full-session ingestion requires longer processing time.
    *   **Location**: `LLM_reflection.py:138`, `ingestion_pipeline.py:75`.

## 4. Known Issues \u0026 Workarounds
*   **JSON Response Wrapping**: DeepSeek API wraps JSON in markdown code blocks (```json...```).
    *   **Impact**: Breaks `json.loads()` if not stripped.
    *   **Fix**: `_strip_markdown_json()` helper function removes markdown before parsing.
