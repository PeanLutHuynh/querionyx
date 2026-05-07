---
title: "Pre-Week 7 Stabilization Implementation Status"
date: 2026-05-07
project: Querionyx V3
---

# Pre-Week 7 Stabilization Status

Querionyx V3 now has a stabilization layer for benchmarkable, reproducible, deployment-aware evaluation before FastAPI and Next.js integration.

## Implemented Runtime Layer

| Area | Artifact |
|---|---|
| Runtime config and ablation toggles | `src/runtime/config.py` |
| Standardized response/query/failure schemas | `src/runtime/schemas.py` |
| JSONL/JSON/CSV logging helpers | `src/runtime/logging.py` |
| p50/p95/p99 latency helpers | `src/runtime/metrics.py` |
| RAM/CPU snapshot support | `src/runtime/metrics.py` |
| Timeout wrapper | `src/runtime/timeouts.py` |
| Deterministic fallback text/templates | `src/runtime/fallbacks.py` |
| Lazy SQL initialization | `src/pipeline_v3.py` |
| Branch-level telemetry | `src/pipeline_v3.py`, `src/hybrid/hybrid_handler.py` |

## Implemented Evaluation Layer

| Area | Artifact |
|---|---|
| Deterministic benchmark runner | `src/evaluation/benchmark_runner.py` |
| Ablation runner | `src/evaluation/eval_runner.py` |
| Aggregation and CSV/JSON export | `src/evaluation/aggregate_results.py` |
| Deterministic scoring | `src/evaluation/scoring.py` |
| Replay support | `src/evaluation/replay.py` |
| Smoke benchmark dataset | `benchmarks/datasets/smoke_9_queries.json` |
| Full benchmark dataset | `benchmarks/datasets/eval_90_queries.json` |
| Router ambiguity dataset | `benchmarks/datasets/router_ambiguity_cases.json` |
| Experiment manifests | `benchmarks/manifests/*.json` |
| Ablation configs | `ablation/configs/*.json` |

## Deployment-Safe Changes

- `QueryonixPipelineV3` no longer initializes `TextToSQLPipeline` during construction when no SQL pipeline is injected.
- SQL schema/database work is lazy and measured on first SQL use.
- Heavy RAG remains disabled by default through `lightweight_rag=true`.
- LLM router and merge LLM remain disabled by default.
- Runtime behavior is controlled through `RuntimeConfig` and ablation JSON files.

## Verified Smoke Run

Command:

```powershell
.\.venv\Scripts\python.exe -m src.evaluation.benchmark_runner `
  --dataset benchmarks\datasets\smoke_9_queries.json `
  --config ablation\configs\full_v3.json `
  --manifest benchmarks\manifests\default_manifest.json `
  --output-dir reports\experiment_runs\pre_week7_smoke_full_v3 `
  --max-latency-ms 8000
```

Observed result:

| Metric | Value |
|---|---:|
| Query count | 9 |
| Pass rate | 1.0 |
| Avg latency | 558.35 ms |
| p50 latency | 716.91 ms |
| p95 latency | 800.36 ms |
| p99 latency | 802.79 ms |
| LLM calls/query | 0.0 |
| Timeout rate | 0.0 |
| Fallback rate | 0.0 |
| Startup time | 1.56 ms |

Output artifacts:

- `reports/experiment_runs/pre_week7_smoke_full_v3/query_logs.jsonl`
- `reports/experiment_runs/pre_week7_smoke_full_v3/failure_logs.jsonl`
- `reports/experiment_runs/pre_week7_smoke_full_v3/results.json`
- `reports/experiment_runs/pre_week7_smoke_full_v3/results.csv`
- `reports/experiment_runs/pre_week7_smoke_full_v3/summary.md`
- `reports/experiment_runs/pre_week7_smoke_full_v3/cold_start.json`

## Verified Ablation Smoke

Command:

```powershell
.\.venv\Scripts\python.exe -m src.evaluation.eval_runner `
  --dataset benchmarks\datasets\smoke_9_queries.json `
  --manifest benchmarks\manifests\default_manifest.json `
  --output-dir reports\experiment_runs\pre_week7_ablation_smoke `
  --max-latency-ms 8000 `
  --limit 3
```

This validates that all required ablation configs are executable and produce aggregate CSV/JSON artifacts.

Output artifacts:

- `reports/experiment_runs/pre_week7_ablation_smoke/ablation_summary.csv`
- `reports/experiment_runs/pre_week7_ablation_smoke/ablation_summary.json`
- `reports/tables/ablation_summary.csv`

## Week 7 Handoff

FastAPI should call `QueryonixPipelineV3.query()` through a service wrapper and preserve these standardized response fields:

- `answer`
- `sources`
- `intent`
- `latency_ms`
- `confidence`
- `router_type_used`
- `llm_call_count`
- `branches`
- `fallback_used`
- `timeout_triggered`
- `sql_success`
- `rag_success`
- `merge_used`
- `answer_nonempty`
- `cache_hit`
- `timings`

Do not expose internal `raw` fields directly to the frontend unless needed for debug mode.
