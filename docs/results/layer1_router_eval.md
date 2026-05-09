# Router Evaluation - 3 Model Comparison

**Timestamp**: 2026-05-09T06:31:50+07:00

## Summary Metrics

| Router | Total | Correct | Accuracy | Avg Latency (ms) | LLM Call Rate |
|--------|-------|---------|----------|------------------|---------------|
| rule_based_router | 150 | 136 | 0.9067 | 0.10 | 0.0000 |
| llm_router | 150 | 45 | 0.3000 | 81.29 | 0.0000 |
| adaptive_router | 150 | 136 | 0.9067 | 0.04 | 0.0000 |

## Per-Class Accuracy

| Router | RAG | SQL | HYBRID |
|--------|-----|-----|--------|
| rule_based_router | 1.0000 | 0.9000 | 0.8200 |
| llm_router | 0.3000 | 0.3200 | 0.2800 |
| adaptive_router | 1.0000 | 0.9000 | 0.8200 |

## Confusion Matrices

### Rule-Based Router

### rule_based_router

| Predicted \ Ground Truth | HYBRID | RAG | SQL |
|--------------------|--------------------|--------------------|--------------------|
| HYBRID | 41 | 0 | 2 |
| RAG | 9 | 50 | 3 |
| SQL | 0 | 0 | 45 |

### llm_router

| Predicted \ Ground Truth | HYBRID | RAG | SQL |
|--------------------|--------------------|--------------------|--------------------|
| HYBRID | 14 | 20 | 19 |
| RAG | 24 | 15 | 15 |
| SQL | 12 | 15 | 16 |

### adaptive_router

| Predicted \ Ground Truth | HYBRID | RAG | SQL |
|--------------------|--------------------|--------------------|--------------------|
| HYBRID | 41 | 0 | 2 |
| RAG | 9 | 50 | 3 |
| SQL | 0 | 0 | 45 |

## Misrouting Breakdown

### rule_based_router

- HYBRID→RAG: 9
- SQL→HYBRID: 2
- SQL→RAG: 3

### llm_router

- HYBRID→RAG: 24
- HYBRID→SQL: 12
- RAG→HYBRID: 20
- RAG→SQL: 15
- SQL→HYBRID: 19
- SQL→RAG: 15

### adaptive_router

- HYBRID→RAG: 9
- SQL→HYBRID: 2
- SQL→RAG: 3
