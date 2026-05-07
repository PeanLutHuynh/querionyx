---
title: "Pre-Week 7 Stabilization Roadmap"
date: 2026-05-07
project: Querionyx V3
phase: "Before FastAPI + Next.js integration"
---

# Pre-Week 7 Stabilization Roadmap

Querionyx V3 should enter Week 7 as a measurable, deterministic-first hybrid RAG + Text-to-SQL system, not merely as a working demo. The immediate goal is to stabilize evaluation, logging, failure recovery, latency instrumentation, and deployment-safe behavior before adding the FastAPI and Next.js layers.

The research contribution should stay focused:

> A lightweight hybrid RAG + Text-to-SQL orchestration pipeline optimized for low-resource deployment environments through deterministic routing, cached SQL planning, lightweight retrieval, adaptive execution, and graceful fallback handling.

This roadmap avoids adding new AI features. It prioritizes measurable systems contribution, reproducibility, weak-hardware readiness, and ICCCNET-style applied AI evaluation.

---

# 1. Prioritized Implementation Checklist

## P0: Required Before Week 7 Integration

| Item | Complexity | Systems-paper value | Deployment stability value | Dependencies | Order |
|---|---:|---|---|---|---:|
| Standardized response schema | Low | Makes all experiments comparable across RAG, SQL, and HYBRID modes | Gives API/frontend one stable contract | Existing `QueryonixPipelineV3.query` output | 1 |
| Query execution log schema | Medium | Enables tables for latency, pass rate, branch usage, LLM calls, and fallback behavior | Makes production incidents diagnosable | Response schema | 2 |
| Failure log schema | Low | Supports robustness analysis and failure taxonomy | Preserves useful error details without crashing requests | Runtime exception boundaries | 3 |
| Timeout hierarchy | Medium | Shows low-resource serving constraints were handled systematically | Prevents hanging requests on Ollama, SQL, or retrieval | Pipeline branch boundaries | 4 |
| Graceful fallback handling | Medium | Demonstrates deterministic-first recovery rather than LLM-heavy rescue | Keeps API responsive even when one branch fails | Timeout hierarchy, failure log | 5 |
| Benchmark harness | Medium | Core artifact for reproducible evaluation | Catches regressions before deployment | Dataset, schemas | 6 |
| Evaluation runner | Medium | Produces repeatable pass-rate and latency results | Validates the deployed behavior matches local behavior | Benchmark harness | 7 |
| Structured metrics logging | Medium | Supports paper figures/tables without manual reconstruction | Centralizes operational signals | Query log, failure log | 8 |
| Deterministic output formatting | Low | Reduces evaluator ambiguity and manual scoring variance | Prevents frontend from parsing inconsistent text | Response schema | 9 |
| SQL failure logging | Low | Shows Text-to-SQL reliability and recovery rate | Allows safe fallback on SQL syntax/runtime errors | Failure log | 10 |
| Fallback logging | Low | Quantifies graceful degradation | Exposes reliability issues early | Failure log, query log | 11 |
| Router ambiguity logging | Low | Supports analysis of adaptive routing weaknesses | Helps prevent bad branch selection in production | Router result object | 12 |
| p50/p95 latency tracking | Low | Essential systems metric for ICCCNET-style evaluation | Reveals tail latency and timeout risks | Metrics aggregator | 13 |
| Ablation toggles | Medium | Enables credible contribution claims against simpler baselines | Lets risky modes be disabled in deployment | Config layer | 14 |

## P1: Strongly Recommended Before Public Demo

| Item | Complexity | Systems-paper value | Deployment stability value | Dependencies | Order |
|---|---:|---|---|---|---:|
| RAM/CPU instrumentation | Medium | Supports low-resource deployment claim | Detects memory spikes and CPU saturation | `psutil` or platform-safe fallback | 15 |
| Startup/cold-start measurement | Medium | Direct evidence for Render/weak-hardware discussion | Exposes model/database initialization cost | Startup wrapper | 16 |
| Reproducibility tooling | Medium | Makes results defendable in thesis/paper | Allows deployment-vs-local comparison | Benchmark runner | 17 |
| CSV + JSON metrics export | Low | CSV for tables, JSON for auditability | Simple artifact inspection | Metrics aggregator | 18 |
| Cache-effect measurement | Medium | Validates SQL planner/cache contribution | Confirms cache works after restart | Benchmark harness | 19 |
| Branch-level latency logging | Medium | Isolates router, SQL, RAG, merge overhead | Identifies slow component before API integration | Instrumented branch wrappers | 20 |
| Lightweight deployment protections | Medium | Shows engineering maturity under constraints | Avoids expensive startup and request-time model loads | Config layer, timeouts | 21 |

## P2: Useful After Core Stabilization

| Item | Complexity | Systems-paper value | Deployment stability value | Dependencies | Order |
|---|---:|---|---|---|---:|
| Chart generation scripts | Low | Speeds paper figure creation | Not required for serving | CSV outputs | 22 |
| Experiment manifest files | Medium | Improves reproducibility across machines | Helps compare deployment environments | Reproducibility tooling | 23 |
| Extended failure taxonomy | Low | Makes robustness section richer | Helps operations triage | Failure logs | 24 |
| Load-test smoke script | Medium | Adds deployment credibility | Catches concurrency issues | API integration later | 25 |

## Suggested Implementation Order

1. Freeze one standardized runtime response schema.
2. Add query execution logging around the existing V3 pipeline.
3. Add failure logging at router, SQL, RAG, merge, and timeout boundaries.
4. Add timeout wrappers and deterministic fallback paths.
5. Build a minimal benchmark harness using existing evaluation queries.
6. Add metrics aggregation for pass rate, latency, p50/p95, LLM calls, fallback rate, and empty answers.
7. Add ablation toggles through config/environment variables.
8. Add CPU/RAM and cold-start measurement.
9. Export benchmark results to JSON and CSV.
10. Only then begin FastAPI integration.

---

# 2. Recommended Folder Structure

Recommended structure:

```text
querionyx/
  src/
    pipeline_v3.py
    hybrid/
    rag/
    router/
    sql/
    runtime/
      schemas.py
      logging.py
      metrics.py
      timeouts.py
      fallbacks.py
      config.py
    evaluation/
      benchmark_runner.py
      eval_runner.py
      aggregate_results.py
      scoring.py
      replay.py
  benchmarks/
    datasets/
      eval_90_queries.json
      smoke_9_queries.json
      router_ambiguity_cases.json
    manifests/
      default_manifest.json
      render_like_manifest.json
  ablation/
    configs/
      full_v3.json
      no_cache.json
      no_parallel.json
      no_hybrid.json
      force_merge_llm.json
      full_rag_mode.json
      sql_only_mode.json
      rag_only_mode.json
    results/
  metrics/
    query_logs/
    failure_logs/
    latency/
    resource_usage/
    cold_start/
  profiling/
    local/
    render_like/
    branch_breakdowns/
  deployment/
    render/
      render.yaml
      env.example
      startup_notes.md
    docker/
      Dockerfile
      docker-compose.yml
      env.example
  reports/
    experiment_runs/
      YYYYMMDD_HHMMSS_full_v3/
        manifest.json
        query_logs.jsonl
        failure_logs.jsonl
        results.json
        results.csv
        summary.md
    tables/
      ablation_summary.csv
      latency_summary.csv
      reliability_summary.csv
    charts/
      latency_p95.png
      ablation_latency.png
      fallback_frequency.png
  docs/
    evaluation/
    research/
    week6/
    week7/
```

Design rules:

- Keep runtime code in `src/runtime`; keep experimental scripts in `src/evaluation`.
- Keep raw benchmark datasets in `benchmarks/datasets`; keep generated outputs in `reports/experiment_runs`.
- Store JSONL logs for append-safe execution; export CSV for paper tables.
- Keep ablation configs outside runtime so deployment defaults remain conservative.
- Keep deployment files isolated from evaluation artifacts.
- Treat `reports/tables` and `reports/charts` as paper-ready generated artifacts.

---

# 3. Standardized JSON Schemas

The implementation can use Python dataclasses or Pydantic later. Before FastAPI, simple dictionaries validated by helper functions are enough.

## A. Query Execution Log

```json
{
  "query_id": "q_0001",
  "question": "Which customers placed the most orders?",
  "intent": "SQL",
  "branches_used": ["sql"],
  "router_type": "adaptive_rule",
  "llm_calls": 0,
  "latency_ms": 184.7,
  "p50_latency": 162.3,
  "p95_latency": 421.9,
  "cpu_percent": 38.5,
  "ram_mb": 512.4,
  "cold_start": false,
  "timeout_triggered": false,
  "fallback_used": false,
  "sql_success": true,
  "rag_success": null,
  "merge_used": false,
  "confidence": 0.94,
  "answer_nonempty": true,
  "timestamp": "2026-05-07T10:25:31+07:00"
}
```

Field notes:

| Field | Type | Meaning |
|---|---|---|
| `query_id` | string | Stable benchmark or request identifier |
| `question` | string | Original user question |
| `intent` | string | `RAG`, `SQL`, `HYBRID`, or `UNKNOWN` |
| `branches_used` | array | Runtime branches actually executed |
| `router_type` | string | `rule_router`, `adaptive_rule`, or `llm_router` |
| `llm_calls` | integer | Total local/remote LLM calls |
| `latency_ms` | number | End-to-end query latency |
| `p50_latency` | number | Rolling or run-level median latency |
| `p95_latency` | number | Rolling or run-level p95 latency |
| `cpu_percent` | number/null | Process or system CPU percent |
| `ram_mb` | number/null | Process RSS memory in MB |
| `cold_start` | boolean | True for first measured request after process start |
| `timeout_triggered` | boolean | True if any timeout fired |
| `fallback_used` | boolean | True if answer used fallback path |
| `sql_success` | boolean/null | SQL branch outcome |
| `rag_success` | boolean/null | RAG branch outcome |
| `merge_used` | boolean | True if merge LLM or merge logic ran |
| `confidence` | number/null | Router or answer confidence |
| `answer_nonempty` | boolean | True if final answer has useful content |
| `timestamp` | string | ISO-8601 timestamp with timezone |

## B. Failure Log

```json
{
  "failure_type": "timeout",
  "stage": "rag_branch",
  "query": "Summarize supplier information and show related order totals.",
  "exception": "RAG branch exceeded 3000 ms timeout",
  "recovery_strategy": "used_sql_branch_only",
  "latency_impact_ms": 3000.0,
  "resolved": true,
  "timestamp": "2026-05-07T10:25:31+07:00"
}
```

Recommended `failure_type` values:

- `timeout`
- `sql_generation_error`
- `sql_execution_error`
- `empty_retrieval`
- `router_ambiguous`
- `merge_error`
- `ollama_unavailable`
- `database_unavailable`
- `unexpected_exception`

Recommended `stage` values:

- `router`
- `sql_planner`
- `sql_execution`
- `rag_retrieval`
- `rag_generation`
- `hybrid_merge`
- `response_formatting`
- `startup`

## C. Ablation Result Log

```json
{
  "config_name": "no_parallel",
  "cache_enabled": true,
  "parallel_enabled": false,
  "lightweight_rag": true,
  "merge_llm_enabled": false,
  "avg_latency": 812.6,
  "p95_latency": 1420.2,
  "avg_ram_mb": 534.1,
  "llm_calls_avg": 0.08,
  "pass_rate": 0.86,
  "sql_success_rate": 0.93,
  "hybrid_success_rate": 0.78
}
```

Add optional fields later only if needed:

- `timeout_rate`
- `fallback_rate`
- `empty_answer_rate`
- `cold_start_ms`
- `dataset_name`
- `run_id`
- `git_commit`

---

# 4. Benchmark / Evaluation Architecture

## Minimal Research-Grade Flow

```text
Load benchmark manifest
  -> Load benchmark dataset
  -> Apply ablation/runtime config
  -> Initialize pipeline
  -> Measure startup/cold-start
  -> Warm up only if manifest says so
  -> Execute queries with deterministic replay
  -> Log query-level JSONL
  -> Log failures JSONL
  -> Aggregate run metrics
  -> Export JSON + CSV
  -> Generate summary markdown
```

## Evaluation Pipeline

1. `benchmark_runner.py`
   - Runs a dataset against one config.
   - Emits query logs and failure logs.
   - Accepts `--config`, `--dataset`, `--output-dir`, `--seed`, `--cold-start`.

2. `eval_runner.py`
   - Runs multiple configs for ablation.
   - Ensures identical query order and seed per config.
   - Writes one folder per experiment run.

3. `aggregate_results.py`
   - Computes pass rate, p50, p95, average RAM, CPU, timeout rate, fallback rate, and branch success rates.
   - Exports `results.json`, `results.csv`, and `summary.md`.

4. `scoring.py`
   - Keeps scoring deterministic.
   - Uses expected intent, non-empty answer, SQL success, answer contains expected keyword, and optional manual labels.
   - Avoids LLM-as-judge for core systems metrics.

5. `replay.py`
   - Replays a saved run using fixed query order and config.
   - Useful for deployment-vs-local comparison.

## Benchmark Dataset Structure

```json
{
  "dataset_name": "eval_90_queries",
  "version": "v3-pre-week7",
  "queries": [
    {
      "query_id": "q_001",
      "question": "Which customers have the most orders?",
      "expected_intent": "SQL",
      "expected_branches": ["sql"],
      "expected_keywords": ["customer", "orders"],
      "requires_sql": true,
      "requires_rag": false,
      "difficulty": "easy",
      "category": "structured_lookup"
    }
  ]
}
```

## Measuring Latency Correctly

- Use `time.perf_counter()` for elapsed time.
- Measure end-to-end latency from just before routing to after standardized response formatting.
- Also record branch-level timings:
  - `router_latency_ms`
  - `sql_latency_ms`
  - `rag_latency_ms`
  - `merge_latency_ms`
  - `formatting_latency_ms`
- Report p50 and p95 from per-query end-to-end latencies.
- Do not include benchmark file loading in per-query latency.
- Do include response formatting, because API users will experience it.

## Measuring Cold Starts

Cold-start measurement should be separate from normal query latency:

- `process_start_to_pipeline_ready_ms`
- `pipeline_init_ms`
- `first_query_latency_ms`
- `first_sql_query_latency_ms`
- `first_rag_query_latency_ms`
- `first_hybrid_query_latency_ms`

For Render-style discussion, report:

- cold start without heavy RAG;
- cold start with full RAG enabled;
- first request after cache already exists;
- first request after cache cleared.

## Measuring Cache Effects

Run each SQL-heavy benchmark in three modes:

1. `cold_cache`: clear planner cache before run.
2. `warm_cache`: run once, then immediately run again.
3. `persistent_cache`: restart process and reuse saved cache.

Report:

- average SQL latency;
- p95 SQL latency;
- SQL success rate;
- planner cache hit rate;
- LLM calls/query.

This directly supports the claim that cached SQL planning reduces latency and LLM dependence.

## Isolating Router Overhead

Add a router-only benchmark:

```text
question -> router -> intent/confidence/reason
```

Do not execute SQL or RAG. Measure:

- router latency;
- router accuracy against expected intent;
- ambiguous rate;
- LLM escalation rate;
- wrong-route rate.

This proves deterministic routing is cheap and stable.

## Evaluating Deterministic-First Systems

Do not evaluate Querionyx as if it were a pure generative QA system. The strongest evaluation is systems-oriented:

- Did the router select the expected mode?
- Did the pipeline avoid unnecessary LLM calls?
- Did the system return a non-empty answer?
- Did SQL execute successfully when required?
- Did HYBRID answer use both branches when useful?
- Did fallback preserve responsiveness when one branch failed?
- Did latency stay within the target budget?
- Did p95 remain acceptable on weak hardware?

---

# 5. Ablation Study Design

| Config | Expected behavior | Expected tradeoffs | Metrics to compare | Systems-paper significance |
|---|---|---|---|---|
| `full_v3` | Deterministic router, SQL cache, lightweight RAG, parallel HYBRID, optional merge disabled by default | Best balance of latency, reliability, and answer coverage | pass rate, p95 latency, RAM, LLM calls/query, fallback rate | Main proposed system |
| `no_cache` | SQL planner cache disabled | More repeated planning cost, more LLM calls if planner escalates | SQL latency, LLM calls/query, SQL success rate | Quantifies cache contribution |
| `no_parallel` | HYBRID branches run sequentially | Lower concurrency pressure but higher HYBRID latency | HYBRID p95 latency, timeout rate, CPU | Quantifies parallel execution benefit |
| `no_hybrid` | Router must choose SQL or RAG only | Simpler but weaker for mixed structured/unstructured questions | hybrid success rate, pass rate, empty-answer rate | Shows value of hybrid orchestration |
| `force_merge_llm` | Merge LLM always used for HYBRID answers | Better narrative coherence sometimes, higher latency and instability | merge latency, LLM calls/query, p95, timeout rate | Shows why optional merge is better on weak hardware |
| `full_rag_mode` | Use full RAG V2 retrieval/model path | Better semantic retrieval, higher memory and cold-start cost | RAG pass rate, RAM, cold start, p95 | Tests lightweight RAG tradeoff |
| `sql_only_mode` | All queries forced through SQL path | Strong on structured questions, fails document questions | SQL success rate, overall pass rate, wrong-mode rate | Baseline for structured-only system |
| `rag_only_mode` | All queries forced through RAG path | May answer document questions but weak on exact database facts | RAG success, pass rate, latency, hallucination/manual flags | Baseline for naive RAG system |

Recommended ablation table columns:

```text
Config | Pass Rate | SQL Success | HYBRID Success | Avg Latency | p95 Latency | Avg RAM | LLM Calls/Query | Timeout Rate | Fallback Rate
```

Best paper argument:

- `full_v3` should beat `rag_only_mode` and `sql_only_mode` on pass rate.
- `full_v3` should beat `force_merge_llm` on latency and LLM calls/query.
- `full_v3` should beat `full_rag_mode` on memory, cold start, and p95 latency.
- `full_v3` should beat `no_hybrid` on HYBRID success.
- `full_v3` should beat `no_cache` on SQL latency and LLM calls/query.

---

# 6. Recommended Metrics

## A. Research Metrics

| Metric | Why it matters | ICCCNET strength |
|---|---|---|
| Pass rate | Overall task success across RAG, SQL, HYBRID | Very strong |
| SQL success rate | Shows structured query reliability | Very strong |
| HYBRID success rate | Measures core contribution, not generic RAG | Very strong |
| Router accuracy | Validates deterministic-first orchestration | Very strong |
| Empty-answer rate | Captures user-visible failure | Strong |
| Fallback frequency | Shows graceful degradation behavior | Strong |
| Ablation delta | Demonstrates each component contributes measurable value | Very strong |

## B. Deployment Metrics

| Metric | Why it matters | ICCCNET strength |
|---|---|---|
| Average latency | Basic serving performance | Strong |
| p95 latency | Tail latency is critical for real deployments | Very strong |
| Startup time | Directly relevant to Render and weak hardware | Very strong |
| Cold-start first query latency | Shows real user impact after idle restart | Very strong |
| Memory usage | Validates low-resource claim | Very strong |
| CPU usage | Shows feasibility under limited compute | Strong |
| Timeout frequency | Indicates serving stability | Strong |

## C. Reliability Metrics

| Metric | Why it matters | ICCCNET strength |
|---|---|---|
| SQL failure rate | Tracks database/planner instability | Strong |
| RAG failure rate | Tracks retrieval/generation instability | Strong |
| Merge failure rate | Shows risk of optional LLM merge | Medium |
| Fallback success rate | Shows failures are contained | Very strong |
| Router ambiguity rate | Identifies uncertain queries before bad execution | Strong |
| Resolved failure rate | Measures recovery quality | Strong |

## D. Cost-Efficiency Metrics

| Metric | Why it matters | ICCCNET strength |
|---|---|---|
| LLM calls/query | Main proxy for local compute cost and latency | Very strong |
| Cache hit rate | Shows deterministic reuse reduces computation | Strong |
| Branches executed/query | Shows router avoids unnecessary work | Strong |
| Merge LLM usage rate | Shows expensive synthesis is optional | Strong |
| Latency per successful answer | Combines performance and usefulness | Strong |

Strongest ICCCNET-style metrics:

1. p95 latency under weak hardware.
2. LLM calls/query.
3. memory usage.
4. cold-start time.
5. ablation pass-rate and latency deltas.
6. fallback success rate.
7. SQL and HYBRID success rates.

---

# 7. Deployment-Safe Backend Recommendations

## Recommended Backend Shape Before FastAPI

Create a single runtime service object:

```text
App startup
  -> load config
  -> initialize lightweight pipeline
  -> initialize SQL connection pool lazily
  -> initialize lightweight RAG chunks
  -> avoid loading heavy embedding model unless enabled
  -> expose query function with timeout/logging/fallback wrappers
```

## Model Loading Strategy

- Default to no LLM call for routing, SQL cache hits, and lightweight RAG.
- Load or contact Ollama lazily only when LLM routing or merge is enabled.
- Add an Ollama health check with a short timeout.
- If Ollama is unavailable, disable LLM-dependent paths for the request and log `ollama_unavailable`.
- Avoid loading local LLM during web server import.

## ChromaDB Lifecycle

- Do not initialize ChromaDB at module import time.
- In default Render-safe mode, use lightweight chunk retrieval.
- If full RAG is enabled, initialize ChromaDB once during startup or first RAG request.
- Cache retrieval objects in the application service, not in per-request handlers.
- Log full RAG startup memory and latency separately.

## PostgreSQL Handling

- Avoid opening a new database connection per query.
- Use a small connection pool once FastAPI is added.
- Before FastAPI, centralize SQL connection creation in a runtime service.
- Add query execution timeout.
- Log SQL syntax errors separately from connection errors.
- Keep generated SQL read-only where possible.

## Async-Safe Execution

- Do not block the event loop with heavy CPU work once FastAPI exists.
- Wrap blocking SQL/RAG calls in thread executors if needed.
- Keep parallel HYBRID execution bounded.
- Cancel slow sibling branches after a successful deterministic answer if policy allows.

## Memory Safety

- Keep lightweight RAG default.
- Avoid duplicating chunk lists per request.
- Avoid storing full raw contexts in every log.
- Truncate logged exceptions and answers.
- Store large artifacts in report files, not in process memory.

## Cache Persistence

- Persist SQL planner cache to disk if stable.
- Add cache versioning tied to schema version.
- Invalidate cache when schema metadata changes.
- Track cache hit/miss in query logs.

## Render Constraints

- Expect cold starts.
- Expect limited RAM.
- Expect process restarts.
- Avoid relying on local Ollama unless deployment explicitly supports it.
- Keep startup under a measurable target.
- Prefer lazy optional components over mandatory heavyweight startup.

## What Not To Do

- Do not load sentence-transformer, ChromaDB, local LLM, and SQL connections at import time.
- Do not call the merge LLM for every HYBRID query.
- Do not let Ollama calls run without timeout.
- Do not hide SQL errors behind generic "failed" messages.
- Do not make the frontend depend on raw internal pipeline fields.
- Do not benchmark only warm-cache local runs and claim deployment readiness.
- Do not add agentic multi-step reasoning before evaluation is stable.

## Common Local LLM Mistakes

- Assuming Ollama is always running.
- Measuring only successful LLM calls and ignoring timeouts.
- Loading a model during app startup on weak hardware.
- Retrying LLM calls too aggressively.
- Treating LLM merge as free because the model is local.
- Forgetting local model memory pressure affects database and retrieval performance.

---

# 8. Timeout + Fallback Design

## Timeout Hierarchy

Recommended starting values for weak hardware:

| Stage | Timeout |
|---|---:|
| Router deterministic rules | 100 ms |
| Router LLM escalation | 2000 ms |
| SQL cache lookup/planning | 500 ms |
| SQL execution | 3000 ms |
| Lightweight RAG retrieval | 1500 ms |
| Full RAG retrieval/generation | 5000 ms |
| HYBRID total budget | 6000 ms |
| Merge LLM | 2500 ms |
| End-to-end request | 8000 ms |

These values should be configurable.

## Graceful Degradation Policy

1. Prefer deterministic answer if available.
2. If SQL succeeds and RAG fails, return SQL answer with `fallback_used=true`.
3. If RAG succeeds and SQL fails, return RAG answer with `fallback_used=true`.
4. If merge fails, return deterministic concatenation of SQL and RAG evidence.
5. If retrieval is empty, return SQL answer if available or a deterministic "insufficient evidence" response.
6. If all branches fail, return a standardized failure response, not an exception traceback.

## Deterministic Fallback Flow

```text
Route query
  -> If route confident: execute selected branch
  -> If route ambiguous: use conservative HYBRID or configured fallback
  -> Apply branch timeouts
  -> Collect successful branch outputs
  -> If one success: return that answer
  -> If two successes and merge disabled: deterministic merge
  -> If two successes and merge enabled: attempt timed merge
  -> If merge fails: deterministic merge
  -> If no success: return standardized unavailable/insufficient evidence response
```

## Retry Policy

- Retry SQL connection failures once if failure is transient.
- Do not retry SQL syntax errors without changing the query.
- Retry Ollama once only for connection startup errors.
- Do not retry LLM timeout during the same request.
- Do not retry empty retrieval; fallback instead.

## Branch Cancellation Logic

- In HYBRID mode, run SQL and RAG concurrently only if both are expected to contribute.
- If one branch fails fast, let the other continue within total budget.
- If total request budget is nearly exhausted, cancel remaining branch and return best available answer.
- Log canceled branches as `timeout` or `cancelled_due_to_budget`.

## Merge-Failure Handling

- Merge LLM must be optional and timed.
- If merge fails, use deterministic template:

```text
Structured result:
{sql_answer}

Document evidence:
{rag_answer}
```

Do not call a second merge LLM.

## Empty-Retrieval Handling

- Return SQL answer if SQL branch succeeded.
- If RAG-only query has empty retrieval, return a deterministic insufficient-evidence response.
- Log `empty_retrieval`.
- Count it in empty-answer or retrieval-failure metrics depending on final response quality.

---

# 9. Pitfalls To Avoid Before Week 7

## Before FastAPI Integration

- Freezing no response schema before writing API routes.
- Letting API routes call internal modules directly without timeout/logging wrappers.
- Loading heavy models during import.
- Returning inconsistent fields for SQL, RAG, and HYBRID.
- Ignoring cancellation behavior for parallel branches.

## Before Next.js Frontend

- Designing UI around unstable raw pipeline fields.
- Showing internal exceptions to users.
- Failing to expose `intent`, `latency_ms`, `fallback_used`, and `sources` in a stable way.
- Assuming every answer has sources.

## Before Docker Deployment

- Copying benchmark outputs into runtime image.
- Baking local `.env` secrets into image.
- Starting Ollama/model services without health checks.
- Running database migrations or indexing on every container start.

## Before Render Deployment

- Assuming persistent disk is always available.
- Assuming local Ollama works the same as local development.
- Using full RAG by default.
- Ignoring cold-start latency.
- Keeping startup dependent on database, vector DB, and LLM all being healthy.

## Before Large-Scale Benchmark Runs

- Mixing cold-start and warm-query latency in one metric.
- Changing query order across ablation configs.
- Running ablations with different caches.
- Reporting only averages without p95.
- Failing to store config and git commit with results.
- Logging too much raw context and exhausting disk/memory.

## Research-Quality Pitfalls

- Claiming model intelligence improvements when the contribution is orchestration.
- Adding more LLM calls instead of measuring deterministic routing.
- Using only anecdotal examples.
- Omitting ablation results.
- Omitting failure cases.
- Not separating RAG, SQL, and HYBRID categories.

## Reproducibility Pitfalls

- No fixed random seed.
- No benchmark manifest.
- No saved config per run.
- No versioned dataset.
- No clear cache state.
- No environment metadata.

## Latency-Measurement Mistakes

- Using wall-clock timestamps instead of monotonic timers for elapsed time.
- Measuring only successful calls.
- Excluding response formatting from end-to-end latency.
- Including dataset loading in per-query latency.
- Reporting p95 from too few queries without saying the sample size.

## Logging Mistakes

- Logging unbounded full answers, full contexts, or full stack traces.
- Logging inconsistent field names.
- Omitting timestamps.
- Omitting fallback and timeout flags.
- Overwriting previous experiment runs.

---

# 10. Minimum Viable Research-Grade Evaluation Pipeline

## Smallest Credible Pipeline

The minimum viable pipeline should include:

1. One benchmark dataset with RAG, SQL, and HYBRID categories.
2. One benchmark runner that executes all queries against one config.
3. One ablation runner that executes required configs.
4. Query-level JSONL logs.
5. Failure-level JSONL logs.
6. Aggregated JSON and CSV outputs.
7. Summary tables for pass rate, latency, p95, memory, LLM calls/query, timeout rate, and fallback rate.
8. A short deployment discussion based on cold-start, memory, and timeout results.

## Benchmark Methodology

- Use the same dataset for all ablations.
- Fix query order and random seed.
- Separate cold-start measurement from warm-run latency.
- Run at least:
  - `smoke_9_queries` for quick regression;
  - `eval_90_queries` for thesis/paper tables.
- Label each query by expected mode:
  - `RAG`;
  - `SQL`;
  - `HYBRID`.

## Required Evaluation Tables

Table 1: Overall performance

```text
System | Pass Rate | Avg Latency | p50 | p95 | Avg RAM | LLM Calls/Query | Empty Answer Rate
```

Table 2: Per-intent performance

```text
Intent | Query Count | Pass Rate | Avg Latency | p95 | Success Rate | Fallback Rate
```

Table 3: Ablation study

```text
Config | Pass Rate | p95 Latency | Avg RAM | LLM Calls/Query | SQL Success | HYBRID Success | Timeout Rate
```

Table 4: Robustness

```text
Failure Type | Count | Resolved Count | Recovery Strategy | Avg Latency Impact
```

Table 5: Deployment readiness

```text
Mode | Startup Time | First Query Latency | Avg RAM | p95 Latency | Notes
```

## Required Analyses

Latency analysis:

- Compare average and p95 latency.
- Explain tail latency causes.
- Separate SQL, RAG, HYBRID, and merge overhead.

Cost analysis:

- Use LLM calls/query as the main cost proxy.
- Compare `full_v3` against `force_merge_llm`, `full_rag_mode`, and `no_cache`.
- Explain why local LLM calls still have memory and latency cost.

Robustness analysis:

- Report timeout frequency.
- Report fallback frequency.
- Report resolved failure rate.
- Include examples of SQL failure, empty retrieval, and merge timeout recovery.

Deployment discussion:

- Discuss cold starts.
- Discuss memory limits.
- Discuss why lightweight RAG is default.
- Discuss Ollama instability and timeout handling.
- Discuss cache persistence and safe startup.

## What Is Sufficient

For a graduation thesis, engineering showcase, or ICCCNET-style short paper, this is enough:

- 90-query mixed benchmark.
- 8 ablation configs.
- p50/p95 latency.
- memory and CPU snapshots.
- LLM calls/query.
- timeout and fallback rates.
- cold-start measurement.
- clear deployment constraints.

## What Is Unnecessary Overengineering

Avoid before Week 7:

- complex online dashboards;
- distributed tracing;
- multi-agent query planning;
- extra LLM judges for every query;
- full synthetic dataset generation pipeline;
- Kubernetes-style deployment abstractions;
- heavy vector retrieval by default;
- advanced reranking unless evaluation proves retrieval is the bottleneck.

## Where To Stop

Stop when the system can answer these questions with saved evidence:

1. Is V3 faster than heavier alternatives under weak hardware?
2. Does V3 reduce LLM calls/query?
3. Does hybrid routing improve mixed-query success?
4. Does caching improve SQL latency?
5. Does graceful fallback prevent user-visible crashes?
6. Can the same benchmark be replayed locally and after deployment?

At that point, the project is ready for Week 7 FastAPI + Next.js integration.

---

# Final Pre-Week-7 Decision

Do not add new AI capabilities before deployment integration. Stabilize the measurement system first.

The strongest Querionyx V3 story is:

> Under low-resource constraints, deterministic orchestration, cached SQL planning, lightweight retrieval, selective parallelism, and graceful fallback can provide practical hybrid RAG + Text-to-SQL behavior with lower latency, lower memory pressure, and fewer LLM calls than heavier alternatives.

