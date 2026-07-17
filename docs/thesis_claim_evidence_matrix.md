# Querionyx Claim-Evidence Matrix

This file is the reporting gate for the thesis. A claim may move to
`Approved` only when its source artifacts satisfy the evaluation policy and
`thesis_reporting_allowed=true` where a manifest is required.

## Evidence Labels

- **Measured:** direct execution or corpus/configuration inspection with traceable inputs.
- **Derived:** reproducible calculation from measured records.
- **Automatically derived:** reproducible scoring from measured outputs and frozen references.
- **Pending execution:** the protocol is frozen but a final content-addressed run does not exist.

## Frozen Claims

| ID | Claim | Evidence | Label | Status | Permitted wording | Required work | Thesis location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | The corpus contains nine FPT, Masan, and Vinamilk reports and 9,670 chunks. | `data/processed/chunks_recursive.json.gz`; `data/source_manifest.json` | Measured | Approved | "The indexed corpus contains nine reports and 9,670 chunks." | None | 3.2, 4.1 |
| C02 | The corpus covers 1,406 distinct per-document page identifiers. | Direct corpus inventory | Derived | Approved with caveat | "The chunks cover 1,406 distinct page identifiers." | None | 3.2 |
| C03 | The deterministic router matches all labels in the curated 150-query set. | `final_router_curated_150` | Measured | Approved with scope | "The router achieved 100% accuracy on the frozen 150-query curated development/validation set." | None | 4.2 |
| C04 | The deterministic router remains effective on adversarial queries. | `final_router_stress` | Measured | Approved with scope | "The router achieved 89% accuracy on the frozen 100-query adversarial stress set." | None | 4.2 |
| C05 | The no-Ollama demo has route and SQL fast-path coverage for the curated set. | `scripts/audit_no_ollama_readiness.py` | Measured/derived | Approved with scope | "All 150 curated prompts passed the static no-Ollama readiness audit." | None | 3.8, appendix |
| C06 | The public artifact uses Vercel, Render, and Supabase in no-Ollama mode. | Deployment configuration and live health check | Measured configuration | Approved with deployment caveat | "The Vercel frontend and Render API were reachable; database availability depends on the configured Supabase secret." | Reset the Render database secret and capture final screenshots | 3.8 |
| C07 | RAG outputs align with the expected company/topic evidence in the frozen benchmark. | `final_90_full_v3/automatic_summary.json` | Automatically derived | Approved with scope | "RAG evidence alignment was 0.8345 across applicable RAG/HYBRID cases in the frozen 90-query benchmark." | None | 4.3 |
| C08 | SQL outputs match independently executed Northwind reference results. | `final_90_full_v3/automatic_summary.json` | Automatically derived | Approved with scope | "SQL result F1 was 1.0000 for applicable SQL/HYBRID cases; technical pass was reported separately." | None | 4.3 |
| C09 | Hybrid variants differ in evidence alignment, branch completion, and latency. | `final_component_hybrid_30/component_automatic_summary.json` | Automatically derived | Approved with scope | "On 30 frozen HYBRID queries, automatic scores were 0.8935 full, 0.9410 dense-only, 0.0347 RAG-only, 0.4020 SQL-only, and 0.8850 no-fallback." | Explain that single-branch variants are intentionally penalized for missing the other branch | 4.4 |
| C10 | Querionyx can be compared with LLM-only Qwen 2.5 3B and Plain RAG under one evidence rubric. | `final_baseline_20/baseline_automatic_summary.json` | Automatically derived | Approved with scope | "On the frozen 20-query baseline, scores were 0.9446 Querionyx, 0.5187 Plain RAG, and 0.2336 LLM-only." | None | 4.5 |
| C11 | Sequential and asynchronous hybrid execution can be compared for latency and exact canonical output equivalence. | `final_async_hybrid/async_automatic_summary.json` | Measured/derived | Approved with scope | "Across 10 paired queries, async execution reduced P50 from 364.55 ms to 338.13 ms and P95 from 993.45 ms to 415.00 ms while preserving 100% exact canonical output matches." | Do not generalize a universal speedup from one local run; report both P50 and P95 | 4.6 |

## Prohibited Interpretations

- "100% router accuracy" without naming the curated benchmark.
- Technical pass rate as a synonym for semantic correctness.
- "1,406 PDF pages"; the measured quantity is per-document page identifiers represented in chunks.
- Public Render latency as equivalent to a local research benchmark.
- Any result without dataset, source-snapshot, configuration, and per-query trace hashes.
- Any baseline or component result produced with different references or score weights across systems.
- Component scores as a general ranking beyond the frozen 30 HYBRID queries.

## Frozen Research Questions

### RQ1: Routing Robustness

How accurately and consistently does the deterministic router classify RAG,
SQL, and HYBRID queries across curated and adversarial enterprise-query sets?

### RQ2: Hybrid Answer Quality and Component Contribution

To what extent does hybrid orchestration improve correctness, groundedness, and
completion of mixed-intent queries compared with reduced configurations?

### RQ3: End-to-End Effectiveness and Efficiency

How does Querionyx compare with LLM-only Qwen 2.5 3B and Plain RAG, and what
latency/reliability trade-offs arise from asynchronous execution and fallback?

RQ1, RQ2, and RQ3 now have content-addressed final evidence. All numerical
claims remain limited to the named frozen datasets and automatic metric scope.

## Change Control

After the evaluation snapshot is frozen, do not modify router patterns, SQL planners,
retrieval logic, benchmark labels, component configs, references, or score weights. Any necessary
runtime fix creates a new evaluation version and requires rerunning affected
experiments.
