# Router Evaluation - 3 Model Comparison

**Timestamp**: 2026-05-08T09:21:48+07:00

## Summary Metrics

| Router | Total | Correct | Accuracy | Avg Latency (ms) | LLM Call Rate |
|--------|-------|---------|----------|------------------|---------------|
| rule_based_router | 90 | 76 | 0.8444 | 0.10 | 0.0000 |
| llm_router | 90 | 38 | 0.4222 | 554.82 | 0.0000 |
| adaptive_router | 90 | 76 | 0.8444 | 0.03 | 0.0000 |

## Per-Class Accuracy

| Router | RAG | SQL | HYBRID |
|--------|-----|-----|--------|
| rule_based_router | 1.0000 | 0.8333 | 0.7000 |
| llm_router | 0.3333 | 0.4667 | 0.4667 |
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
| HYBRID | 14 | 13 | 9 |
| RAG | 11 | 10 | 7 |
| SQL | 5 | 7 | 14 |

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
- HYBRID→SQL: 5
- RAG→HYBRID: 13
- RAG→SQL: 7
- SQL→HYBRID: 9
- SQL→RAG: 7

### adaptive_router

- HYBRID→RAG: 9
- SQL→HYBRID: 2
- SQL→RAG: 3
