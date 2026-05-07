---
title: "Week 7 Status - Deployment and Production Layer"
date: 2026-05-07
project: Querionyx V3
---

# Week 7 Status

Querionyx V3 now has an external production layer built around the frozen V3 core.

## Completed

- FastAPI backend at [backend/main.py](C:/Data/Project/querionyx/backend/main.py)
- Production service wrapper at [services/query_service.py](C:/Data/Project/querionyx/services/query_service.py)
- Pre-pipeline TTL response cache with real cache-hit behavior
- External HYBRID orchestration in the service layer with parallel SQL/RAG execution
- Streaming endpoint at `POST /query/stream`
- Health and metrics endpoints
- PDF upload path with chunking and optional embedding/Chroma insert
- Router stress script at [src/evaluation/router_stress_test.py](C:/Data/Project/querionyx/src/evaluation/router_stress_test.py)
- UAT runner at [src/uat/run_uat.py](C:/Data/Project/querionyx/src/uat/run_uat.py)
- Next.js frontend scaffold in [frontend](C:/Data/Project/querionyx/frontend)
- Production Docker updates for backend/frontend/postgres/chromadb

## Verified

- Frontend production build succeeds with `npm run build`
- Router stress test runs on 60 cases
- `/health`, `/metrics`, `/query`, and `/query/stream` respond correctly
- 90-query UAT plus 10 repeated cache checks completed without crashes

## Current Measured Signals

- Router stress:
  `router_accuracy = 0.9167`
  `misrouting_rate = 0.0833`
  `confidence_calibration_error = 0.1067`
- UAT:
  `non_crash_rate = 1.0`
  `non_empty_rate = 1.0`
  `timeout_rate = 0.0`
  `cache_hit_rate = 0.1`

## Notes

- The cache requirement is now satisfied: repeat queries return `cache_hit=true`.
- Week 7 orchestration stays outside [src/pipeline_v3.py](C:/Data/Project/querionyx/src/pipeline_v3.py).
- The generated SQL cache file under `data/cache/text_to_sql_cache.json` changed during verification and should not be committed unless you explicitly want refreshed cache contents in Git.
