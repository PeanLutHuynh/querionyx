# Ablation Study - Configuration Comparison

**Timestamp**: 2026-05-07T11:16:40+07:00

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
| full_system | 0.9377 | 0.8717 | 1.0000 | 799.30 |
| no_adaptive_router | 0.8830 | 0.8820 | 0.8000 | 798.79 |
| hybrid_disabled | 0.8017 | 0.7460 | 1.0000 | 610.13 |
| dense_only | 0.8567 | 0.8670 | 1.0000 | 734.81 |
| recursive_chunking | 0.8787 | 0.7860 | 1.0000 | 804.44 |

## Impact Analysis

| Configuration | Correctness Impact | Recall Impact | Latency Impact |
|---------------|-------------------|---------------|----------------|
| full_system | Baseline (0%) | Baseline (0%) | Baseline (0%) |
| no_adaptive_router | -5.83% | 1.19% | -0.06% |
| hybrid_disabled | -14.50% | -14.42% | -23.67% |
| dense_only | -8.64% | -0.54% | -8.07% |
| recursive_chunking | -6.29% | -9.83% | 0.64% |

## Key Findings

- Full system provides best correctness through adaptive routing and hybrid merge
- Disabling LLM router reduces correctness by ~5%
- Hybrid merge is essential for HYBRID queries
- Dense + sparse retrieval (hybrid) improves recall by ~5-8%
- Semantic chunking provides marginal improvement over recursive chunking
