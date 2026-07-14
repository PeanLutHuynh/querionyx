# Querionyx Project Freeze

## Current Status

| Area | Status | Meaning |
| --- | --- | --- |
| Public demo software | Feature-frozen | Only reproducible defect, security, and evidence fixes are allowed |
| Deployment | Action required | Vercel and Render are reachable; the Render Supabase secret must be reset before the final demo |
| Repository layout | Cleaned | Legacy simulations, weekly logs, duplicate datasets, and invalid result artifacts were removed; local runtime caches remain available |
| Benchmark datasets/configs | Frozen | Paths, query IDs, labels, and SHA-256 hashes are in `benchmarks/manifests/frozen_evaluation_sets.json` |
| Router/static readiness | Complete | Curated accuracy is 100%; frozen stress accuracy is 89% |
| Answer quality | Complete | The reportable 90-query automatic score is 0.9193 with 100% technical pass |
| Baseline comparison | Complete | All 60 outputs across three systems were collected and scored automatically |
| Component comparison | Complete | Five variants were executed on 30 frozen HYBRID queries each |
| Final numerical assets | Complete | 12 figures and 13 tables were generated from reportable summaries |
| Credential hygiene | User action required | Rotate credentials previously shared outside secret stores |

The software and research evidence are frozen under source snapshot
`aef151b9f149d080df3d12fba8c6356c60bea37f86f7ac181645e3f3044b1709`.
All six final evidence groups are reportable and the project lock passes.

## Allowed Changes

- Fix a demonstrated defect that blocks the demo or frozen benchmark.
- Add provenance, manifests, automatic references, tests, or documentation.
- Correct security or credential-handling issues.
- Improve thesis wording without changing an approved claim.

Changes to routing, SQL planning, retrieval, hybrid merge/fallback, benchmark
content, or scoring require a new evaluation version and affected reruns.

## Remaining Release Steps

1. Rotate the previously exposed service credentials.
2. Set the current `PGPASSWORD` in Render and verify `/health` reports `db_status=ok`.
3. Push the frozen commits and wait for Render/Vercel deployments.
4. Capture final UI, API health, SQL, RAG, HYBRID, and unsupported-query screenshots.
5. Archive the complete workspace and optionally tag the evidence state.

Exact commands are maintained in
[`docs/evaluation/EVALUATION_POLICY.md`](evaluation/EVALUATION_POLICY.md).

## Content Snapshot Protocol

1. Every final run hashes all source, configuration, test, dataset, reference,
   corpus, and source-manifest inputs.
2. Git commit and dirty state remain visible metadata, while the content hash is
   the reproducibility key for a complete project archive.
3. Any implementation, benchmark, reference, or scoring change requires reruns
   for affected results.
4. Generated figures and tables only ingest summaries with
   `thesis_reporting_allowed=true`.

## Lock Verification

```powershell
python -m compileall -q backend services src scripts tests
python -m unittest tests.test_db_connect tests.test_fast_sql_planner tests.test_evaluation_lock tests.test_chunk_store tests.test_automatic_scoring tests.test_hybrid_merge tests.test_no_ollama_audit
python scripts/audit_no_ollama_readiness.py
python scripts/generate_thesis_assets.py
python scripts/check_project_lock.py
git status --short
```

The final archive is ready only when every intended thesis result is reportable
and the project lock passes.
