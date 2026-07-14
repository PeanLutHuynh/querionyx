# Benchmark Summary

- Query count: 90
- Pass rate: 1.0
- Automatic evidence score: 0.9193
- Automatic pass rate: 0.9444
- SQL result F1: 1.0
- RAG evidence score: 0.8345
- Hybrid integration score: 0.9917
- Avg latency: 112.39 ms
- p50 latency: 98.75 ms
- p95 latency: 203.87 ms
- p99 latency: 484.11 ms
- LLM calls/query: 0.0
- Timeout rate: 0.0
- Fallback rate: 0.0111
- Cache hit rate: 0.0

## Per Intent

| Intent | Queries | Technical pass | Automatic score | Automatic pass | Avg latency | p95 latency | Fallback rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| RAG | 30 | 1.0 | 0.788 | 0.8333 | 80.8 | 93.73 | 0.0 |
| SQL | 30 | 1.0 | 1.0 | 1.0 | 133.89 | 234.38 | 0.0 |
| HYBRID | 30 | 1.0 | 0.9698 | 1.0 | 122.49 | 171.26 | 0.0333 |
