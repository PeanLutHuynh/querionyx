# Hybrid Query Evaluation

**Timestamp**: 2026-05-09T07:37:51+07:00

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Queries | 50 |
| Correct | 44 |
| Hybrid Correctness Score | 0.8150 |
| Fallback Rate | 0.2600 |

## Latency Metrics

| Percentile | Latency (ms) |
|------------|--------------|
| P50 | 761.28 |
| P95 | 1007.31 |
| P99 | 1307.41 |
| Average | 790.93 |

## Component Contribution Breakdown

| Component | Count | Percentage |
|-----------|-------|------------|
| both_fail | 6 | 12.0% |
| full_merge | 37 | 74.0% |
| rag_fallback | 7 | 14.0% |

## Component Descriptions

### Full Merge (SQL + RAG)
Results from both SQL and RAG engines contribute evidence to the final answer.
A separate LLM merge is optional; this category is counted whenever both branches succeed.
Expected to have highest quality but higher latency than single-branch answers.

### SQL Fallback
Fallback to SQL only when RAG retrieval confidence is low.
Used when entity-based questions have ambiguity.

### RAG Fallback
Fallback to RAG only when SQL generation fails.
Used for text-heavy questions that cannot be structured.

## Coherence Evaluation

**Note**: Human annotation required for full coherence scoring.
Current implementation provides structural readiness for manual review.
