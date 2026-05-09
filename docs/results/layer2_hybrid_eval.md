# Hybrid Query Evaluation

**Timestamp**: 2026-05-09T06:37:54+07:00

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Queries | 50 |
| Correct | 50 |
| Hybrid Correctness Score | 0.9050 |
| Fallback Rate | 1.0000 |

## Latency Metrics

| Percentile | Latency (ms) |
|------------|--------------|
| P50 | 730.26 |
| P95 | 6021.52 |
| P99 | 6028.54 |
| Average | 1604.27 |

## Component Contribution Breakdown

| Component | Count | Percentage |
|-----------|-------|------------|
| rag_fallback | 15 | 30.0% |
| sql_fallback | 35 | 70.0% |

## Component Descriptions

### Full Merge (SQL + RAG)
Results from both SQL and RAG engines merged and ranked.
Expected to have highest quality but highest latency.

### SQL Fallback
Fallback to SQL only when RAG retrieval confidence is low.
Used when entity-based questions have ambiguity.

### RAG Fallback
Fallback to RAG only when SQL generation fails.
Used for text-heavy questions that cannot be structured.

## Coherence Evaluation

**Note**: Human annotation required for full coherence scoring.
Current implementation provides structural readiness for manual review.
