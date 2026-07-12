# Querionyx

Querionyx is a graduation project that answers natural-language questions over two evidence sources:

- **Northwind PostgreSQL data** for structured questions, such as product counts and top customers.
- **Annual-report documents** for grounded company questions about FPT, Vinamilk, and Masan.

The system routes each question to SQL, retrieval-augmented generation (RAG), or both. Its production demo is intentionally designed to work without Ollama: common SQL intents use deterministic query plans and document answers use lightweight evidence-based retrieval.

## Highlights

- Bilingual Vietnamese and English question routing.
- SQL fast paths for stable Northwind demo questions.
- Lightweight RAG with source citations from annual-report chunks.
- Hybrid execution that combines database and document evidence.
- Explicit insufficient-evidence response for unsupported or low-confidence questions.
- Debug traces, latency metrics, cache status, health checks, and a streaming API.
- Evaluation scripts and reproducible benchmark artifacts for the thesis.

## Live Demo

- Web application: `https://querionyx.vercel.app/`
- API health check: `https://querionyx.onrender.com/health`

## Architecture

```text
Question
   |
Rule-based router
   |---- SQL ------> deterministic planner -> PostgreSQL -> table / answer
   |---- RAG ------> lightweight retriever -> annual-report chunks -> cited answer
   '---> HYBRID ---> SQL and RAG in parallel -> evidence-aware combined answer
                                      |
                                FastAPI response
                                      |
                                Next.js interface
```

`backend/main.py` exposes the API. `services/query_service.py` handles caching, metrics, streaming, uploads, and response serialization. The core pipeline lives in `src/`.

## Project Structure

```text
querionyx/
├── backend/                    # FastAPI entry point
├── frontend/                   # Next.js demo interface
├── services/                   # API-facing orchestration, cache, and metrics
├── src/
│   ├── hybrid/                 # Hybrid SQL + RAG execution
│   ├── rag/                    # RAG baselines and retrieval implementations
│   ├── router/                 # Rule-based and optional Ollama routers
│   ├── runtime/                # Timeouts, schemas, logging, fallbacks, config
│   ├── sql/                    # Text-to-SQL planner and PostgreSQL execution
│   ├── evaluation/             # Thesis benchmark and paper-asset scripts
│   ├── data_prep/              # PDF inspection, chunking, and index utilities
│   └── uat/                    # User-acceptance test runner
├── scripts/                    # Small developer and demo utilities
├── tests/                      # Focused automated tests
├── data/
│   ├── processed/              # Versioned document chunks required by lightweight RAG
│   ├── cache/                  # SQL planning cache
│   └── test_queries/           # Evaluation datasets
├── benchmarks/                 # Benchmark manifests and smoke datasets
├── deployment/
│   ├── render/                 # Render Blueprint and environment template
│   └── docker/                 # Local Docker Compose configurations
├── docs/                       # Deployment, evaluation, results, and paper artifacts
└── run.ps1                     # Windows helper for local Docker/API/test commands
```

## Requirements

- Python 3.12 recommended.
- Node.js 22 recommended for the frontend.
- A PostgreSQL database containing the Northwind schema and data.
- The tracked `data/processed/chunks_recursive.pkl` file for lightweight RAG.

Ollama is optional for local research experiments. It is not required for the deployed demo configuration.

## Local Setup

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item deployment\render\env.example .env
```

Edit `.env` with your PostgreSQL credentials. For a Supabase connection pooler, use `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, and `PGSSLMODE=require`.

Run the API:

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000/docs` for the interactive API documentation or check `http://localhost:8000/health`.

### 2. Frontend

```powershell
cd frontend
npm ci
$env:NEXT_PUBLIC_API_BASE = "http://localhost:8000"
npm run dev
```

Open `http://localhost:3000`.

### 3. Local Docker demo

The full-stack Compose file starts PostgreSQL, ChromaDB, the backend, and the frontend:

```powershell
.\run.ps1 up
.\run.ps1 ps
.\run.ps1 logs
.\run.ps1 down
```

The alternative `deployment/docker/docker-compose.remote-db.yml` starts only the application services and expects a reachable external database.

## Environment Configuration

For the Render demo, use the template in [deployment/render/env.example](deployment/render/env.example). The important no-Ollama configuration is:

```env
ENABLE_HEAVY_RAG=0
QUERIONYX_LIGHTWEIGHT_RAG=1
QUERIONYX_CACHE_ENABLED=1
QUERIONYX_MERGE_LLM_ENABLED=0
QUERIONYX_USE_LLM_ROUTER=0
QUERIONYX_RAG_LOW_CONFIDENCE_THRESHOLD=0.6
QUERIONYX_LIGHTWEIGHT_RAG_MS=4000
QUERIONYX_SQL_EXECUTION_MS=5000
QUERIONYX_END_TO_END_MS=10000
```

Set `PGPASSWORD` only in the hosting provider's secret manager. Never commit `.env`, database passwords, or service tokens.

For Vercel, configure:

```env
NEXT_PUBLIC_API_BASE=https://querionyx.onrender.com
```

## Demo Prompts

Use prompts within the supported evidence scope. The system can answer paraphrases, but these are the most reliable live-demo questions.

| Mode | Prompts |
| --- | --- |
| SQL | `Có bao nhiêu sản phẩm trong cơ sở dữ liệu?`<br>`Top 5 customers by number of orders.`<br>`Which product sold the most?`<br>`Sản phẩm bán chạy nhất.`<br>`Top khách hàng theo tổng chi tiêu là ai?` |
| RAG | `Tóm tắt rủi ro trong báo cáo của FPT.`<br>`Ban lãnh đạo FPT gồm những ai?`<br>`Chiến lược tăng trưởng của Vinamilk là gì?`<br>`Masan đề cập cơ hội nào trong tài liệu?` |
| Hybrid | `Theo báo cáo FPT năm 2023, chiến lược chính là gì và hiện có bao nhiêu đơn hàng trong hệ thống?`<br>`Masan trình bày chuỗi cung ứng ra sao và top 5 sản phẩm bán chạy là gì?` |
| Unsupported | `Giá cổ phiếu Vinamilk hiện tại là bao nhiêu?`<br>`Công thức bí mật sản xuất sữa của Vinamilk là gì?` |

For unsupported questions, the expected behavior is the explicit Vietnamese insufficient-evidence response, not a fabricated answer.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/query` | Run a question through the pipeline. |
| `POST` | `/query/stream` | Receive server-sent events for a query. |
| `POST` | `/upload` | Add a PDF to the local chunk store; embedding is optional. |
| `GET` | `/health` | Check service, database, RAG, and cache status. |
| `GET` | `/metrics` | Inspect request, latency, cache, and routing metrics. |

Example request:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Which product sold the most?", "debug":true}'
```

## Verification

Run focused regression tests:

```powershell
python -m unittest tests.test_db_connect tests.test_fast_sql_planner
```

Audit the no-Ollama demo coverage without needing a database, embedding model, or LLM:

```powershell
python scripts/audit_no_ollama_readiness.py
```

The audit reads the 150-query evaluation set and writes a report to `docs/evaluation/no_ollama_readiness.md`. Before a defense, run both commands and verify `/health` in the deployed API.

For the broader thesis evaluation workflow, see [docs/EVALUATION_PIPELINE.md](docs/EVALUATION_PIPELINE.md) and the paper-ready artifacts in [docs/paper_assets](docs/paper_assets/README.md).

## Deployment

- **Backend:** Render Blueprint at [deployment/render/render.yaml](deployment/render/render.yaml).
- **Frontend:** Vercel project rooted at `frontend/`.
- **Database:** Supabase PostgreSQL with SSL required.

The backend is deployed from the `backend/` directory, while the Render build installs Python dependencies from the repository root. The render blueprint deliberately disables heavy RAG and LLM routing so the public demo remains reproducible on a small web service.

## Scope and Limitations

Querionyx is a demonstrator and research artifact, not a general-purpose assistant. Its answer quality is bounded by the Northwind database, the indexed annual reports, and the supported routing/planning patterns. Cache entries improve repeat-query latency only; they do not add knowledge or make unsupported questions answerable.

## Documentation

- [Deployment demo checklist](docs/deployment_demo_checklist.md)
- [No-Ollama readiness report](docs/evaluation/no_ollama_readiness.md)
- [Evaluation pipeline](docs/EVALUATION_PIPELINE.md)
- [Northwind schema notes](docs/data_prep/northwind_schema.md)
- [Paper assets](docs/paper_assets/README.md)

---

Querionyx is maintained as a graduation project for the 2025-2026 academic year.
