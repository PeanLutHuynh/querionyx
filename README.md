# Querionyx

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB)]()
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)]()
[![Next.js](https://img.shields.io/badge/UI-Next.js-111111)]()
[![PostgreSQL](https://img.shields.io/badge/Data-PostgreSQL-4169E1)]()
[![Evaluation](https://img.shields.io/badge/Evaluation-real--only-0F766E)]()

Querionyx is a graduation-project demonstrator for answering bilingual natural-
language questions across two enterprise evidence sources:

- Northwind PostgreSQL for structured, aggregative questions.
- FPT, Masan, and Vinamilk annual reports for cited document questions.

The router selects SQL, RAG, or parallel HYBRID execution. The deployed demo is
designed to run without Ollama by combining deterministic SQL planners with a
lightweight extractive retriever.

Configured deployments:

- Frontend: `https://querionyx.vercel.app/`
- Backend: `https://querionyx.onrender.com/`

## What Is Included

- Vietnamese and English rule-based routing.
- Deterministic Northwind SQL fast paths with read-only validation.
- A safe, compressed corpus of 9,670 chunks from nine annual reports.
- Lightweight cited RAG for small hosting instances.
- Optional dense + BM25 retrieval and Ollama generation for local research.
- Parallel HYBRID execution, timeout/fallback traces, cache metrics, and SSE.
- Frozen datasets, configs, references, and content-addressed manifests.
- Real-only evaluation collectors; simulated legacy results are not retained.

The static no-Ollama audit currently covers 150 curated prompts, including 100
SQL/HYBRID prompts requiring deterministic SQL plans. This is implementation
coverage, not a semantic answer-quality claim.

## Final Evaluation Snapshot

All result artifacts below share source snapshot
`76ed4ff2c1f0ea25d0011b8f8006b6cd02b2fe680b29b2463f448d357bb2294e`
and pass the project evidence gate.

| Evaluation | Final result |
| --- | ---: |
| 90-query automatic evidence score | 0.9193 |
| 90-query automatic pass rate | 94.44% |
| 90-query technical pass rate | 100% |
| SQL result F1 | 1.0000 |
| RAG evidence alignment | 0.8345 |
| HYBRID integration score | 0.9917 |
| Router accuracy, curated 150 | 100% |
| Router accuracy, stress 100 | 89% |
| Sequential / async P50, 10 paired queries | 364.55 / 338.13 ms |
| Sequential / async P95, 10 paired queries | 993.45 / 415.00 ms |
| Async exact canonical output matches | 100% |

On the frozen 20-query baseline, automatic evidence scores were `0.9446` for
Querionyx, `0.5187` for Plain RAG, and `0.2336` for LLM-only Qwen 2.5 3B.
These values are bounded reference/evidence metrics for the named datasets.

## Architecture

![Querionyx architecture](docs/thesis_assets/figures/fig01_system_architecture.png)

```text
Question -> Rule router
             |-- RAG -----> compressed report chunks ------|
             |-- SQL -----> PostgreSQL ---------------------|-> answer + trace
             '-- HYBRID --> RAG and SQL in parallel --------|
```

FastAPI exposes the application through `backend/main.py`. API orchestration,
caching and metrics live in `services/query_service.py`; the frozen
pipeline is implemented under `src/`.

## Quick Start

### 1. Backend

Requirements: Python 3.12 and a PostgreSQL database containing the Northwind
schema. Ollama and embedding models are not needed for public-demo mode.

```powershell
git clone <repository-url>
cd querionyx
Copy-Item .env.example .env
.\run.ps1 setup
.\run.ps1 api
```

Edit `.env` with your database connection first. Open:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Without a database, the API and document path still start, while SQL requests
return an explicit unavailable/insufficient-evidence result.

### 2. Frontend

Requirements: Node.js 22.

```powershell
.\run.ps1 frontend
```

Open `http://localhost:3000`. The default API base is
`http://localhost:8000`.

### 3. Docker

The Compose stack builds the backend and frontend but deliberately expects an
external Northwind PostgreSQL service; it does not ship a misleading empty
database container.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Dependency Tiers

The default clone remains small by separating runtime and research packages.

```powershell
# FastAPI, PostgreSQL, and lightweight RAG
pip install -r requirements.txt

# Optional ChromaDB, sentence transformers, Ollama, and thesis figures
pip install -r requirements-research.txt
```

Downloaded models, Chroma indexes, raw PDFs, virtual environments, Next build
output, metrics, and non-final experiment runs are ignored by Git.

## Demo Prompts

| Path | Example |
| --- | --- |
| SQL | `Which product sold the most?` |
| SQL | `Top 5 customers by number of orders.` |
| RAG | `Tóm tắt rủi ro trong báo cáo của FPT.` |
| RAG | `Ban lãnh đạo FPT gồm những ai?` |
| RAG | `Chiến lược tăng trưởng của Vinamilk là gì?` |
| HYBRID | `Masan trình bày chuỗi cung ứng ra sao và top 5 sản phẩm bán chạy là gì?` |
| Unsupported | `Giá cổ phiếu Vinamilk hiện tại là bao nhiêu?` |

Unsupported or weakly supported questions must return the explicit
insufficient-evidence response rather than a fabricated answer.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/query` | Execute one query. |
| `POST` | `/query/stream` | Stream metadata and result with SSE. |
| `GET` | `/health` | Inspect API, database, RAG, and cache health. |
| `GET` | `/metrics` | Inspect latency, cache, routing, and failures. |

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Which product sold the most?","debug":true}'
```

## Verification

The clone-level checks do not require PostgreSQL, Ollama, ChromaDB, or model
downloads:

```powershell
.\run.ps1 check
```

Equivalent commands:

```powershell
python -m compileall -q backend services src scripts tests
python -m unittest tests.test_db_connect tests.test_fast_sql_planner tests.test_evaluation_lock tests.test_chunk_store tests.test_automatic_scoring tests.test_hybrid_merge tests.test_no_ollama_audit
python scripts/audit_no_ollama_readiness.py
python scripts/check_project_lock.py
```

## Research Workflow

Evaluation is fully automatic and fail-closed. SQL is scored by row-level
equivalence against independent read-only references; RAG is scored by expected
company/topic evidence, citations, and extractive overlap; HYBRID additionally
checks both-branch completion and integration. These are bounded evidence
metrics, not an unqualified free-form semantic-correctness score.

```powershell
.\run.ps1 research-setup
python -m src.data_prep.reindex_chromadb
```

Run the complete evaluation and regenerate report assets with:

```powershell
.\run.ps1 evaluate
```

The exact protocol is documented in the
[evaluation policy](docs/evaluation/EVALUATION_POLICY.md). Final runs record the
source snapshot, dataset/config/reference hashes, environment, and per-query
traces. Missing services or references fail the run instead of producing a
placeholder score.

Regenerate report-ready design/setup assets with:

```powershell
.\run.ps1 assets
```

## Project Structure

```text
querionyx/
|-- backend/                 FastAPI entry point and runtime image
|-- frontend/                Next.js demo interface
|-- services/                API orchestration, cache, and metrics
|-- src/
|   |-- router/              deterministic and optional Ollama routing
|   |-- sql/                 planner, validation, PostgreSQL execution
|   |-- rag/                 optional dense + sparse local RAG
|   |-- hybrid/              parallel branch execution and merge/fallback
|   |-- runtime/             config, traces, timeouts, chunk store
|   |-- evaluation/          real-only benchmark and provenance tools
|   '-- data_prep/           PDF inspection, chunking, dense indexing
|-- benchmarks/              frozen datasets, configs, and manifests
|-- data/                    compressed corpus and source checksums
|-- scripts/                 setup checks, evidence gates, asset export
|-- tests/                   focused unit/regression tests
|-- deployment/render/       Render Blueprint
|-- docs/                    current deployment and thesis governance
|-- compose.yaml             lightweight backend + frontend stack
`-- run.ps1                 Windows command runner
```

## Data and Reproducibility

`data/processed/chunks_recursive.json.gz` is compressed UTF-8 JSON rather than
Pickle. It is safe to inspect and reduces the tracked corpus from about 5.4 MiB
to about 1.4 MiB. Original PDFs are excluded from Git; their filenames, sizes,
and SHA-256 checksums are recorded in
[`data/source_manifest.json`](data/source_manifest.json).

Runtime Text-to-SQL cache files are also excluded. Cache improves repeated
latency only and is never treated as training data, knowledge, or evaluation
evidence.

## Deployment

- Render: [`deployment/render/render.yaml`](deployment/render/render.yaml)
- Vercel: set the project root to `frontend/`
- Database: PostgreSQL/Supabase with SSL for hosted connections
- Secrets: configure only in `.env` locally or the hosting secret manager

Live verification on 2026-07-15 returned HTTP 200 from both Vercel and Render,
and Render loaded all 9,670 chunks. Render reported the Supabase database as
unavailable while the same database passed the local reference runs, so reset
the Render `PGPASSWORD` secret and verify `db_status=ok` before the final demo.

See the [deployment checklist](docs/deployment_demo_checklist.md) before a
defense demo.

## Scope

Querionyx is a bounded research demonstrator, not a general-purpose assistant.
Its answers are limited to the indexed annual reports, the connected Northwind
database, and supported planners/retrieval behavior. Current claim status is
tracked in the [claim-evidence matrix](docs/thesis_claim_evidence_matrix.md).

## Documentation

- [Project freeze](docs/PROJECT_FREEZE.md)
- [Evaluation policy](docs/evaluation/EVALUATION_POLICY.md)
- [Claim-evidence matrix](docs/thesis_claim_evidence_matrix.md)
- [Thesis asset catalog](docs/thesis_assets/README.md)
- [Northwind schema notes](docs/data_prep/northwind_schema.md)
- [Data layout and source verification](data/README.md)
