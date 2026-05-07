---
title: "Week 6 - HYBRID Handler and Queryonix Pipeline V3"
date: 2026-05-06
project: Querionyx
version: 0.6.0
---

# Week 6 Summary: HYBRID Query Handler + Pipeline V3

## Executive Summary

Week 6 integrated the existing RAG V2, router, and Week 5 Text-to-SQL module into a V3 pipeline designed for weak local hardware and future Render deployment.

The main design principle is to avoid unnecessary LLM calls:

- SQL questions use the Text-to-SQL fast planner/cache first.
- RAG questions use lightweight retrieval by default.
- HYBRID questions run SQL and RAG branches in parallel when both are useful.
- Merge LLM is optional and only used when deterministic merging is insufficient.

This is a practical deployment-oriented design rather than an LLM-heavy architecture.

---

## Implemented Artifacts

| Artifact | Path |
|---|---|
| HYBRID handler | `src/hybrid/hybrid_handler.py` |
| V3 pipeline | `src/pipeline_v3.py` |
| Integration smoke test | `src/integration_test_v3.py` |
| Integration result JSON | `docs/week6/integration_test_v3.json` |

---

## HYBRID Handler

**Class:** `HybridQueryHandler`

The handler implements:

- light pre-planning to skip unnecessary branches;
- SQL execution through `TextToSQLPipeline.query(..., include_nl_answer=False)`;
- lightweight RAG retrieval from preprocessed chunks by default;
- parallel SQL/RAG branch execution using `asyncio.gather`;
- deterministic SQL-only, RAG-only, and fallback answers;
- optional LLM merge for complementary SQL and document evidence.

### Render-Oriented RAG Mode

The original RAG V2 pipeline loads a sentence-transformer model and ChromaDB, which can be expensive during cold starts. For V3, the hybrid handler defaults to a lightweight retrieval mode based on cached document chunks and keyword overlap.

To use full RAG V2 retrieval, set:

```powershell
$env:ENABLE_HEAVY_RAG='1'
```

The default lightweight mode is intentionally conservative and optimized for responsiveness.

---

## Pipeline V3

**Class:** `QueryonixPipelineV3`

Output structure:

```json
{
  "answer": "...",
  "sources": [],
  "intent": "RAG|SQL|HYBRID",
  "latency_ms": 123.4,
  "confidence": 1.0,
  "reason": "...",
  "router_type_used": "rule_router|adaptive_rule|llm_router",
  "llm_call_count": 0,
  "branches": ["rag", "sql"],
  "raw": {}
}
```

The adaptive router currently uses rule-based routing by default and only escalates to LLM routing when explicitly enabled. This keeps the V3 path stable for weak hardware.

---

## Integration Smoke Test

The integration test uses 9 cases from `eval_90_queries.json`:

- 3 RAG
- 3 SQL
- 3 HYBRID

Observed result:

| Group | Cases | Status | Notes |
|---|---:|---|---|
| RAG | 3 | Passed | Lightweight retrieval, no LLM calls |
| SQL | 3 | Passed | Fast planner/cache path |
| HYBRID | 3 | Passed | Parallel RAG + SQL, deterministic merge |

All 9 cases returned non-empty answers under the 15s latency target.

Example run summary:

| Case | Intent | Latency Range | LLM Calls |
|---|---|---:|---:|
| RAG | RAG | ~1.3s-2.2s | 0 |
| SQL | SQL | ~0.1s-0.3s | 0 |
| HYBRID | HYBRID | ~1.0s-1.3s | 0 |

---

## Scope and Limitations

This implementation is optimized for local and Render-style constraints. It intentionally favors deterministic handling and cached artifacts over repeated local LLM calls.

Limitations:

- Lightweight RAG retrieval is less semantically rich than full RAG V2.
- Merge LLM remains available but should be used sparingly due to local `qwen2.5:3b` latency.
- Full RAG V2 should be enabled only when the deployment environment can tolerate model loading and retrieval overhead.

The design is suitable for an interactive demo and a system-oriented paper discussion: the contribution is not that the local LLM solves every query, but that the system coordinates routing, SQL planning, retrieval, and fallback policies under a practical latency budget.

---

## Status

Week 6 core integration is complete and smoke-tested.
