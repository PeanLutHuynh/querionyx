# RAG Pipeline V2 (Hybrid Search) - Evaluation Report

**Date:** 2026-05-05
**Model:** Hybrid Dense (ChromaDB) + Sparse (BM25) with RRF Fusion

---

## V2 Summary Metrics

| Metric | Value |
|---|---|
| Context Precision | 0.967 |
| Context Recall | 0.612 |
| Avg Retrieval Latency | 141.60 ms |
| Median Retrieval Latency | 138.94 ms |

## Top-K Coverage Analysis

| K | Avg Context Recall |
|---|---|
| 3 | 0.669 |
| 5 | 0.673 |

## Cross-Entity Drift Analysis

Average off-topic company retrieval rate: 6.7%

*Lower is better: indicates focused retrieval within mentioned companies.*

## Hard Negatives (Fail-Closed Test)

Queries with correct 'not found' response: 4/5
Fail-closed rate: 80.0%

## Detailed Results Table

| Question ID | Precision | Recall | Latency (ms) | Top-3 Recall | Top-5 Recall | Drift |
|---|---|---|---|---|---|---|
| RAG-V2-001 | 1.000 | 0.332 | 182.3 | 0.696 | 0.696 | 0.0% |
| RAG-V2-002 | 1.000 | 0.654 | 132.3 | 0.747 | 0.747 | 0.0% |
| RAG-V2-003 | 1.000 | 0.635 | 145.0 | 0.602 | 0.643 | 66.7% |
| RAG-V2-004 | 1.000 | 0.552 | 155.2 | 0.671 | 0.671 | 0.0% |
| RAG-V2-005 | 1.000 | 0.819 | 134.0 | 0.845 | 0.845 | 0.0% |
| RAG-V2-006 | 1.000 | 0.717 | 160.1 | 0.738 | 0.738 | 0.0% |
| RAG-V2-007 | 0.667 | 0.565 | 135.6 | 0.566 | 0.566 | 0.0% |
| RAG-V2-008 | 1.000 | 0.586 | 142.3 | 0.565 | 0.565 | 0.0% |
| RAG-V2-009 | 1.000 | 0.558 | 118.6 | 0.558 | 0.558 | 0.0% |
| RAG-V2-010 | 1.000 | 0.700 | 110.8 | 0.700 | 0.700 | 0.0% |

---

## Conclusions

- **Hybrid Search Benefit:** RRF fusion combines dense semantic understanding with sparse keyword matching.
- **Top-3 Sufficiency:** With final_top_k=3, most queries achieve reasonable recall while keeping LLM context manageable.
- **Drift Control:** Cross-entity drift metrics indicate how well the system stays focused on relevant document sources.
