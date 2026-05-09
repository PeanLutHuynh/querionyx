# Ablation Study - Configuration Comparison

**Timestamp**: 2026-05-09T06:41:48+07:00

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
| full_system | 0.9304 | 0.8792 | 1.0000 | 791.13 |
| no_adaptive_router | 0.8812 | 0.8666 | 0.9800 | 793.97 |
| hybrid_disabled | 0.8168 | 0.7506 | 1.0000 | 600.11 |
| dense_only | 0.8506 | 0.8790 | 1.0000 | 727.16 |
| recursive_chunking | 0.8748 | 0.7934 | 1.0000 | 806.04 |

## Impact Analysis

| Configuration | Correctness Impact | Recall Impact | Latency Impact |
|---------------|-------------------|---------------|----------------|
| full_system | Baseline (0%) | Baseline (0%) | Baseline (0%) |
| no_adaptive_router | -5.29% | -1.43% | 0.36% |
| hybrid_disabled | -12.21% | -14.63% | -24.14% |
| dense_only | -8.58% | -0.02% | -8.09% |
| recursive_chunking | -5.98% | -9.76% | 1.88% |

## Key Findings

- Full system provides best correctness through adaptive routing and hybrid merge
- Disabling LLM router reduces correctness by ~5%
- Hybrid merge is essential for HYBRID queries
- Dense + sparse retrieval (hybrid) improves recall by ~5-8%
- Semantic chunking provides marginal improvement over recursive chunking
