# No-Ollama Demo Readiness Audit

This is a static route/planner coverage audit. It does not measure answer correctness, retrieval quality, database availability, or latency.

- Dataset: `benchmarks/datasets/eval_150_queries.json`
- Dataset SHA-256: `e023155a6fa492fe6871156a634eab7263b1133ca2c30ccba154bcca644f6232`
- Router SHA-256: `fcea768016b88740503e7a2373caea4088a5f906e810fc0683d3e3c21b6c6a0e`
- SQL planner SHA-256: `ddf1717de729f5cd1803f834b7b7674388fb896287fbe8314f1586420ad2bea7`

## Summary

- Total queries: 150
- Router accuracy: 100.00%
- No-Ollama safe rate: 100.00%
- Queries needing SQL branch: 100
- Queries with SQL fast path: 100
- Issues: `{}`

## Risky Queries

| ID | Expected | Predicted | Fast SQL | Issues | Question |
| --- | --- | --- | --- | --- | --- |
