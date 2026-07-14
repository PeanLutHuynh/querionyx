# Querionyx Thesis Assets

These assets are generated only from the current source tree, frozen benchmark files, the versioned chunk corpus, and reportable automatic summaries.
Reportable final summary groups included: answer_quality, async, baseline, components.

- Source commit: `c0b782cb59f6d3c6f95e2eb5b0d5b886a9927ed8`
- Working tree dirty at generation: `yes`
- Regenerate: `python scripts/generate_thesis_assets.py`

## Figures

| Asset | Caption | Placement |
| --- | --- | --- |
| `fig01_system_architecture.png` / `.svg` | Querionyx runtime architecture | Chapter 3 |
| `fig02_benchmark_intent_distribution.png` / `.svg` | Benchmark intent composition | Chapter 4 setup |
| `fig03_benchmark_difficulty_distribution.png` / `.svg` | Benchmark difficulty composition | Chapter 4 setup |
| `fig04_router_recall_by_intent.png` / `.svg` | Router recall by intent | Chapter 4 routing |
| `fig05_router_stress_confusion_matrix.png` / `.svg` | Stress-test confusion matrix | Chapter 4 error analysis |
| `fig06_no_ollama_readiness.png` / `.svg` | Static no-Ollama readiness | Chapter 3 deployment |
| `fig07_corpus_chunks_by_report.png` / `.svg` | Annual-report chunk distribution | Chapter 3 data |
| `fig08_claim_evidence_readiness.png` / `.svg` | Claim-evidence readiness | Appendix |
| `fig09_answer_quality.png` / `.svg` | Automatic evidence score by intent | Chapter 4 results |
| `fig10_baseline_comparison.png` / `.svg` | Frozen baseline comparison | Chapter 4 results |
| `fig11_component_comparison.png` / `.svg` | Frozen component comparison | Chapter 4 ablation |
| `fig12_async_latency.png` / `.svg` | Sequential and asynchronous latency | Chapter 4 efficiency |

## Tables

| Asset | Rows |
| --- | ---: |
| `table01_benchmark_composition.csv` / `.md` | 3 |
| `table02_router_performance.csv` / `.md` | 8 |
| `table03_router_stress_confusion_matrix.csv` / `.md` | 3 |
| `table04_no_ollama_readiness.csv` / `.md` | 5 |
| `table05_annual_report_corpus.csv` / `.md` | 10 |
| `table06_frozen_runtime_configuration.csv` / `.md` | 12 |
| `table07_api_endpoints.csv` / `.md` | 4 |
| `table08_claim_evidence_status.csv` / `.md` | 11 |
| `table09_asset_provenance.csv` / `.md` | 14 |
| `table10_answer_quality.csv` / `.md` | 4 |
| `table11_baseline_comparison.csv` / `.md` | 3 |
| `table12_component_comparison.csv` / `.md` | 5 |
| `table13_async_hybrid.csv` / `.md` | 8 |

## Reporting Boundary

- Router metrics must name the exact curated or stress dataset.
- No-Ollama readiness is static route/planner coverage, not semantic correctness.
- Corpus page counts are distinct page identifiers represented in chunks.
- Blocked claims in the claim-evidence matrix must not appear as findings.
- Generate final performance assets only after `scripts/check_project_lock.py` marks the corresponding evidence artifacts reportable.
