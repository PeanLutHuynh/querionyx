# Benchmarks

This directory is the single source of truth for evaluation inputs.

## Datasets

| File | Cases | Purpose |
| --- | ---: | --- |
| `datasets/eval_150_queries.json` | 150 | Curated bilingual router and no-Ollama readiness audit |
| `datasets/eval_90_queries.json` | 90 | Balanced RAG, SQL, and HYBRID answer-quality evaluation |
| `datasets/router_stress_100.json` | 100 | Adversarial router robustness |
| `datasets/smoke_9_queries.json` | 9 | Fast local pipeline smoke test |

## References

`references/eval_90_sql_references.json` contains independent read-only SQL
templates and the frozen case-to-template mapping used for row-level result
equivalence. RAG expectations are derived from the benchmark's company and
topic annotations; no LLM judge is used.

## Configurations

- `configs/full_v3.json`: deployed lightweight system configuration.
- `configs/component_full.json`: dense + BM25 full research variant.
- `configs/component_dense_only.json`: dense retrieval without BM25 fusion.
- `configs/component_rag_only.json`: document branch only.
- `configs/component_sql_only.json`: structured branch only.
- `configs/component_no_fallback.json`: full retrieval with partial fallback disabled.

`manifests/frozen_evaluation_sets.json` records dataset/config SHA-256 hashes,
the 20-query baseline selection, and the 30-query component selection. Changing
questions, labels, query IDs, configs, or source files requires a new manifest
version and affected experiment reruns.
