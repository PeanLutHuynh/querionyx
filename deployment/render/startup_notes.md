# Render Startup Notes

- Keep lightweight RAG enabled by default.
- Do not require Ollama during application startup.
- Initialize database access lazily and fail gracefully if unavailable.
- Measure `pipeline_init_ms` and first-query latency separately.
- Keep merge LLM and LLM router disabled unless the environment explicitly supports them.

