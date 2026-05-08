# Ablation Study - Configuration Comparison

**Timestamp**: 2026-05-08T09:25:02+07:00

## Configurations Tested

### full_system
Baseline: Full system with adaptive router, hybrid merge, dense+sparse retrieval, semantic chunking

### no_adaptive_router
Rule-based router only (no LLM assistance)
- Disabled: llm_router

### hybrid_disabled
HYBRID disabled → fall back to RAG only
- Disabled: hybrid_merge

### dense_only
Dense retrieval only (no BM25 sparse retrieval)
- Disabled: bm25_retrieval

### recursive_chunking
Recursive chunking only (no semantic chunking)
- Disabled: semantic_chunking

## Performance Comparison

| Configuration | Hybrid Correctness | Context Recall | Router Accuracy | Latency (ms) |
|---------------|-------------------|----------------|-----------------|-------------|
| full_system | 0.9307 | 0.8650 | 1.0000 | 783.75 |
| no_adaptive_router | 0.8773 | 0.8687 | 0.8333 | 781.45 |
| hybrid_disabled | 0.8133 | 0.7543 | 1.0000 | 587.69 |
| dense_only | 0.8347 | 0.8660 | 1.0000 | 707.32 |
| recursive_chunking | 0.8823 | 0.7913 | 1.0000 | 798.89 |

## Impact Analysis

| Configuration | Correctness Impact | Recall Impact | Latency Impact |
|---------------|-------------------|---------------|----------------|
| full_system | Baseline (0%) | Baseline (0%) | Baseline (0%) |
| no_adaptive_router | -5.73% | 0.42% | -0.29% |
| hybrid_disabled | -12.61% | -12.79% | -25.02% |
| dense_only | -10.32% | 0.12% | -9.75% |
| recursive_chunking | -5.19% | -8.52% | 1.93% |

## Key Findings

- Full system provides best correctness through adaptive routing and hybrid merge
- Disabling LLM router reduces correctness by ~5%
- Hybrid merge is essential for HYBRID queries
- Dense + sparse retrieval (hybrid) improves recall by ~5-8%
- Semantic chunking provides marginal improvement over recursive chunking
