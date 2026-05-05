# RAG Pipeline V2 (Hybrid Search) - Evaluation Report

**Date:** 2026-05-05
**Model:** Hybrid Dense (ChromaDB) + Sparse (BM25) with RRF Fusion

---

## V2 Summary Metrics

| Metric | Value |
|---|---|
| Context Precision | 0.967 |
| Context Recall | 0.618 |
| Avg Retrieval Latency | 152.66 ms |
| Median Retrieval Latency | 148.00 ms |

## Top-K Coverage Analysis

| K | Avg Context Recall |
|---|---|
| 3 | 0.618 |
| 5 | 0.618 |

## Cross-Entity Drift Analysis

Average off-topic company retrieval rate: 13.3%

*Lower is better: indicates focused retrieval within mentioned companies.*

## Hard Negatives (Fail-Closed Test)

Queries with correct 'not found' response: 3/5
Fail-closed rate: 60.0%

## Detailed Results Table

| Question ID | Precision | Recall | Latency (ms) | Top-3 Recall | Top-5 Recall | Drift |
|---|---|---|---|---|---|---|
| RAG-V2-001 | 1.000 | 0.688 | 179.5 | 0.688 | 0.688 | 0.0% |
| RAG-V2-002 | 1.000 | 0.758 | 137.2 | 0.758 | 0.758 | 0.0% |
| RAG-V2-003 | 1.000 | 0.635 | 204.6 | 0.635 | 0.635 | 33.3% |
| RAG-V2-004 | 1.000 | 0.578 | 153.8 | 0.578 | 0.578 | 33.3% |
| RAG-V2-005 | 1.000 | 0.819 | 124.8 | 0.819 | 0.819 | 0.0% |
| RAG-V2-006 | 1.000 | 0.574 | 152.1 | 0.574 | 0.574 | 0.0% |
| RAG-V2-007 | 0.667 | 0.282 | 131.0 | 0.282 | 0.282 | 33.3% |
| RAG-V2-008 | 1.000 | 0.586 | 143.9 | 0.586 | 0.586 | 0.0% |
| RAG-V2-009 | 1.000 | 0.558 | 122.0 | 0.558 | 0.558 | 0.0% |
| RAG-V2-010 | 1.000 | 0.700 | 177.6 | 0.700 | 0.700 | 33.3% |

---

## Conclusions

- **Hybrid Search Benefit:** RRF fusion combines dense semantic understanding with sparse keyword matching.
- **Top-3 Sufficiency:** With final_top_k=3, most queries achieve reasonable recall while keeping LLM context manageable.
- **Drift Control:** Cross-entity drift metrics indicate how well the system stays focused on relevant document sources.
