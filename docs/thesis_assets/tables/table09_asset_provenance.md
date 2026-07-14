| Asset group | Source | SHA-256 | Evidence type | Reporting boundary |
| --- | --- | --- | --- | --- |
| Curated benchmark | benchmarks/datasets/eval_150_queries.json | e023155a6fa492fe6871156a634eab7263b1133ca2c30ccba154bcca644f6232 | Direct dataset inventory | Development/validation set |
| Answer-quality benchmark | benchmarks/datasets/eval_90_queries.json | 2190d358ebe53016c7c7371c0acc37009e81308600ede4f859cb234f81e0c149 | Direct dataset inventory | Experimental setup only until executed |
| Router stress benchmark | benchmarks/datasets/router_stress_100.json | f5e86afc110ef652b4622e217752bd78cabd82d7071b05a3624d71e1dfa93363 | Direct dataset inventory | Adversarial routing set |
| Router implementation | src/router/rule_based_router.py | fcea768016b88740503e7a2373caea4088a5f906e810fc0683d3e3c21b6c6a0e | Measured deterministic execution | Name the evaluated dataset |
| No-Ollama audit | scripts/audit_no_ollama_readiness.py | 961b28965b1fc1ae9c2a3688b5ac402a685dcda823ecec9e10bce0a9a7b29666 | Static executable audit | Not semantic answer quality |
| Corpus summary | data/processed/chunks_recursive.json.gz | 12fcd9ad0a2036b483380fd4b07506fc2ea1126702a09e6d15abdeee86a932d9 | Direct corpus inventory | Page IDs are not physical page totals |
| Source manifest | data/source_manifest.json | 9a3a97c997276a9d6bc2d7338ff36d2dc73b6657665ce9d26e739d253a67e99b | Source-file inventory | Original PDFs are outside Git |
| Frozen configuration | benchmarks/configs/full_v3.json | 42e3f3877d4f4da396fa25a005cf4299e3eab5acacca3348ac30466ff359130e | Configuration inspection | Not performance evidence |
| API surface | backend/main.py | c88461873eb888b6b328b71b2c9974130edc2a355940ba2ea671d5b8380056f8 | Source inspection | Not performance evidence |
| Claim status | docs/thesis_claim_evidence_matrix.md | f38ab0b69393ac8747c1b1c8527266d4447ba373bbe6c76f8171c52bf7163bec | Research governance | Blocked claims remain unreportable |
| Final answer quality | reports/experiment_runs/final_90_full_v3/automatic_summary.json | d8ebe9ab4485877f912e0cbc807ce288fe53344d1fc42e1d11ef7c6b765406f2 | measured | thesis_reporting_allowed=true |
| Final baseline | reports/experiment_runs/final_baseline_20/baseline_automatic_summary.json | 2dd4ce2776a1e63c9578bb337cfb7fd5bc5309e1506f98694416cfca58f4acb0 | measured | thesis_reporting_allowed=true |
| Final components | reports/experiment_runs/final_component_hybrid_30/component_automatic_summary.json | e7bfcb388165290507f3ae6e6672eb5132b762f87a14073ecdc29ce1242f6d6d | measured | thesis_reporting_allowed=true |
| Final async | reports/experiment_runs/final_async_hybrid/async_automatic_summary.json | ae649c8852e769ec88f3ab6e7ecb1ce1d05d447f12ec2ec81ea3fe1d35aa73c2 | measured | thesis_reporting_allowed=true |
