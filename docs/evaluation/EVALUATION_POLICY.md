# Thesis Evaluation Policy

Querionyx evaluation is automatic, deterministic where reference data exists,
and fail-closed. An unavailable database, retriever, or Ollama service is a
measured failure; no simulated output or placeholder score is substituted.

## Evidence Model

Every final run records:

- SHA-256 hashes for the source snapshot, dataset, configuration, SQL reference,
  compressed corpus, and source manifest.
- Runtime environment and hardware metadata.
- Per-query routing, branch, SQL, retrieval, answer, failure, and latency traces.
- A transparent automatic score with its component metrics.

The Git commit and dirty state are recorded for orientation. Reproducibility is
gated by the content-addressed source snapshot, so the complete project ZIP can
be rerun even when it was not produced from a tagged commit.

## Automatic Score

The automatic score is an **evidence-alignment score**, not a human opinion and
not an unrestricted semantic-correctness claim.

| Intent | Automatically measured components |
| --- | --- |
| SQL | Route match, real execution success, and row-level F1 against independent read-only reference SQL |
| RAG | Route match, retrieval success, expected-company citation match, expected-topic coverage, and extractive answer overlap |
| HYBRID | Route match, SQL result equivalence, RAG evidence alignment, both-branch completion, and recorded merge |

The pass threshold is `0.70`. Technical pass rate remains separate from the
automatic evidence score. Exact sequential/async equivalence is measured with a
canonical output fingerprint.

## Reporting Boundary

- SQL result F1 is a strong correctness measure for the frozen Northwind data.
- RAG evidence alignment measures whether the retrieved/cited evidence matches
  expected company and topic signals; it does not prove every sentence is
  semantically complete.
- Baseline and component systems receive the same automatic rubric.
- No result is reportable unless its manifest sets
  `thesis_reporting_allowed=true`.

## Final Commands

```powershell
# Main 90-query run
python -m src.evaluation.benchmark_runner `
  --dataset benchmarks/datasets/eval_90_queries.json `
  --config benchmarks/configs/full_v3.json `
  --manifest benchmarks/manifests/default_manifest.json `
  --references benchmarks/references/eval_90_sql_references.json `
  --output-dir reports/experiment_runs/final_90_full_v3

# Router robustness
python -m src.evaluation.router_stress_test `
  --dataset benchmarks/datasets/eval_150_queries.json `
  --execution-mode evaluation_real `
  --output-dir reports/experiment_runs/final_router_curated_150

python -m src.evaluation.router_stress_test `
  --dataset benchmarks/datasets/router_stress_100.json `
  --execution-mode evaluation_real `
  --output-dir reports/experiment_runs/final_router_stress

# LLM-only, Plain RAG, and Querionyx
python -m src.evaluation.collect_baseline_outputs `
  --execution-mode evaluation_real `
  --output-dir reports/experiment_runs/final_baseline_20

# Full, Dense-only, RAG-only, SQL-only, and No-fallback
python -m src.evaluation.collect_component_outputs `
  --output-dir reports/experiment_runs/final_component_hybrid_30

# Sequential/async latency and exact output equivalence
python -m src.evaluation.benchmark_async_hybrid `
  --execution-mode evaluation_real `
  --output reports/experiment_runs/final_async_hybrid

# Figures, tables, and evidence gate
python scripts/generate_thesis_assets.py
python scripts/check_project_lock.py
```

The complete sequence is exposed as `./run.ps1 evaluate`.
