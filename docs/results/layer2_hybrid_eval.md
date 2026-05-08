# Hybrid Query Evaluation

**Timestamp**: 2026-05-08T09:22:44+07:00

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Queries | 30 |
| Correct | 30 |
| Hybrid Correctness Score | 0.9150 |
| Fallback Rate | 1.0000 |

## Latency Metrics

| Percentile | Latency (ms) |
|------------|--------------|
| P50 | 773.40 |
| P95 | 960.19 |
| P99 | 1688.76 |
| Average | 805.58 |

## Component Contribution Breakdown

| Component | Count | Percentage |
|-----------|-------|------------|
| rag_fallback | 7 | 23.3% |
| sql_fallback | 23 | 76.7% |

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
