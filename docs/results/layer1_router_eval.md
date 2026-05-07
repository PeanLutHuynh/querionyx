# Router Evaluation - 3 Model Comparison

**Timestamp**: 2026-05-07T11:12:45+07:00

## Summary Metrics

| Router | Total | Correct | Accuracy | Avg Latency (ms) | LLM Call Rate |
|--------|-------|---------|----------|------------------|---------------|
| rule_based_router | 90 | 76 | 0.8444 | 0.08 | 0.0000 |
| llm_router | 90 | 30 | 0.3333 | 108.72 | 0.0000 |
| adaptive_router | 90 | 76 | 0.8444 | 0.02 | 0.0000 |

## Per-Class Accuracy

| Router | RAG | SQL | HYBRID |
|--------|-----|-----|--------|
| rule_based_router | 1.0000 | 0.8333 | 0.7000 |
| llm_router | 0.2667 | 0.3333 | 0.4000 |
| adaptive_router | 1.0000 | 0.8333 | 0.7000 |

## Confusion Matrices

### Rule-Based Router

### rule_based_router

| Predicted \ Ground Truth | HYBRID | RAG | SQL |
|--------------------|--------------------|--------------------|--------------------|
| HYBRID | 21 | 0 | 2 |
| RAG | 9 | 30 | 3 |
| SQL | 0 | 0 | 25 |

### llm_router

| Predicted \ Ground Truth | HYBRID | RAG | SQL |
|--------------------|--------------------|--------------------|--------------------|
| HYBRID | 12 | 11 | 13 |
| RAG | 11 | 8 | 7 |
| SQL | 7 | 11 | 10 |

### adaptive_router

| Predicted \ Ground Truth | HYBRID | RAG | SQL |
|--------------------|--------------------|--------------------|--------------------|
| HYBRID | 21 | 0 | 2 |
| RAG | 9 | 30 | 3 |
| SQL | 0 | 0 | 25 |

## Misrouting Breakdown

### rule_based_router

- HYBRID→RAG: 9
- SQL→HYBRID: 2
- SQL→RAG: 3

### llm_router

- HYBRID→RAG: 11
- HYBRID→SQL: 7
- RAG→HYBRID: 11
- RAG→SQL: 11
- SQL→HYBRID: 13
- SQL→RAG: 7

### adaptive_router

- HYBRID→RAG: 9
- SQL→HYBRID: 2
- SQL→RAG: 3
