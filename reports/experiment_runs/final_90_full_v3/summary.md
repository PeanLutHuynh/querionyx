# Benchmark Summary

- Query count: 90
- Pass rate: 1.0
- Automatic evidence score: 0.9193
- Automatic pass rate: 0.9444
- SQL result F1: 1.0
- RAG evidence score: 0.8345
- Hybrid integration score: 0.9917
- Avg latency: 102.55 ms
- p50 latency: 87.34 ms
- p95 latency: 159.35 ms
- p99 latency: 377.27 ms
- LLM calls/query: 0.0
- Timeout rate: 0.0
- Fallback rate: 0.0111
- Cache hit rate: 0.0

## Per Intent

| Intent | Queries | Technical pass | Automatic score | Automatic pass | Avg latency | p95 latency | Fallback rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| RAG | 30 | 1.0 | 0.788 | 0.8333 | 80.51 | 79.64 | 0.0 |
| SQL | 30 | 1.0 | 1.0 | 1.0 | 114.47 | 196.61 | 0.0 |
| HYBRID | 30 | 1.0 | 0.9698 | 1.0 | 112.65 | 128.01 | 0.0333 |
