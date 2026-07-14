# Benchmark Summary

- Query count: 90
- Pass rate: 1.0
- Automatic evidence score: 0.9193
- Automatic pass rate: 0.9444
- SQL result F1: 1.0
- RAG evidence score: 0.8345
- Hybrid integration score: 0.9917
- Avg latency: 114.48 ms
- p50 latency: 95.5 ms
- p95 latency: 208.15 ms
- p99 latency: 462.13 ms
- LLM calls/query: 0.0
- Timeout rate: 0.0
- Fallback rate: 0.0111
- Cache hit rate: 0.0

## Per Intent

| Intent | Queries | Technical pass | Automatic score | Automatic pass | Avg latency | p95 latency | Fallback rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| RAG | 30 | 1.0 | 0.788 | 0.8333 | 89.76 | 76.45 | 0.0 |
| SQL | 30 | 1.0 | 1.0 | 1.0 | 123.08 | 230.96 | 0.0 |
| HYBRID | 30 | 1.0 | 0.9698 | 1.0 | 130.6 | 206.53 | 0.0333 |
