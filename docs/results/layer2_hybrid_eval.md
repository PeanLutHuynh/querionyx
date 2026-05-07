# Hybrid Query Evaluation

**Timestamp**: 2026-05-07T11:14:20+07:00

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Queries | 30 |
| Correct | 24 |
| Hybrid Correctness Score | 0.8500 |
| Fallback Rate | 0.5667 |

## Latency Metrics

| Percentile | Latency (ms) |
|------------|--------------|
| P50 | 722.11 |
| P95 | 849.70 |
| P99 | 849.82 |
| Average | 716.46 |

## Component Contribution Breakdown

| Component | Count | Percentage |
|-----------|-------|------------|
| full_merge | 13 | 43.3% |
| rag_fallback | 6 | 20.0% |
| sql_fallback | 11 | 36.7% |

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
