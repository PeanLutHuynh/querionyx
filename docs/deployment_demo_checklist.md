# Deployment Demo Checklist

## Before Deploying

```powershell
python -m unittest tests.test_db_connect tests.test_fast_sql_planner tests.test_evaluation_lock
python scripts/audit_no_ollama_readiness.py
python scripts/check_project_lock.py
```

Expected static audit: 150/150 routes covered and 100/100 SQL-required
questions matched by deterministic planners. This is readiness coverage, not
semantic answer quality.

## Render Backend

The tracked `data/processed/chunks_recursive.json.gz` file must be present. It
contains 9,670 chunks from nine FPT, Masan, and Vinamilk reports.

Keep the public service in no-Ollama mode:

```env
QUERIONYX_EXECUTION_MODE=demo_no_ollama
ENABLE_HEAVY_RAG=0
QUERIONYX_LIGHTWEIGHT_RAG=1
QUERIONYX_MERGE_LLM_ENABLED=0
QUERIONYX_USE_LLM_ROUTER=0
PGSSLMODE=require
```

Configure `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` in
Render. Store the password only as a secret environment variable.

Verify `/health` reports:

```text
status: ok
db_status: ok
rag_status.chunks_file: ok
rag_status.chunk_count: 9670
```

## Vercel Frontend

Set `NEXT_PUBLIC_API_BASE` to the Render backend origin and redeploy after any
change. Confirm the browser has no CORS or mixed-content errors.

## Defense Smoke Test

Run one prompt from each path:

```text
SQL: Which product sold the most?
RAG: Tóm tắt rủi ro trong báo cáo của FPT.
HYBRID: Masan trình bày chuỗi cung ứng ra sao và top 5 sản phẩm bán chạy là gì?
Unsupported: Giá cổ phiếu Vinamilk hiện tại là bao nhiêu?
```

Check the intent, source citations, SQL table, trace ID, latency, and explicit
insufficient-evidence response. Repeat one supported prompt to demonstrate that
cache affects latency only; it does not add knowledge.

## Deployment Order

1. Rotate previously shared credentials.
2. Deploy Render and validate `/health` and `/metrics`.
3. Deploy Vercel with the final API base URL.
4. Run the four-path smoke test from the public UI.
5. Capture dated health and UI screenshots for the thesis appendix.
