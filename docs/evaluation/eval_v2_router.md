# LLM-based Router V2 - Evaluation Report

**Date:** 2026-05-05
**Test Set:** 60 labeled router queries (20 RAG, 20 SQL, 20 HYBRID)

---

## V1 (Rule-based) Summary

| Metric | Value |
|---|---|
| Overall Accuracy | 91.67% |
| RAG Accuracy | 100.00% |
| SQL Accuracy | 100.00% |
| HYBRID Accuracy | 75.00% |
| Avg Latency | 0.018 ms |
| P95 Latency | 0.026 ms |

## V2 (LLM-based) Summary

| Metric | Value |
|---|---|
| Overall Accuracy | 96.67% |
| RAG Accuracy | 100.00% |
| SQL Accuracy | 100.00% |
| HYBRID Accuracy | 90.00% |
| Avg Latency | 1149.282 ms |
| P95 Latency | 5796.996 ms |
| LLM Call Rate | 8.33% |
| Rule-based Skips | 55 / 60 |

## V1 vs V2 Comparison

| Metric | V1 | V2 | Change |
|---|---|---|---|
| Overall Accuracy | 91.67% | 96.67% | +5.00% |
| RAG Accuracy | 100.00% | 100.00% | +0.00% |
| SQL Accuracy | 100.00% | 100.00% | +0.00% |
| HYBRID Accuracy | 75.00% | 90.00% | +15.00% |
| Avg Latency (ms) | 0.02 | 1149.28 | +1149.26 |

## V2 Efficiency Analysis

- **LLM Calls:** 5 / 60 (8.3%)
- **Rule-based Shortcuts:** 55 queries skipped LLM (direct rule-based)
- **Efficiency Gain:** 91.7% reduction in LLM calls vs full LLM classification

## Confusion Matrices

### V1 (Rule-based) Confusion Matrix

| Predicted \ Ground Truth | RAG | SQL | HYBRID |
|---|---|---|---|
| RAG | 20 | 0 | 0 |
| SQL | 0 | 20 | 0 |
| HYBRID | 5 | 0 | 15 |

### V2 (LLM-based) Confusion Matrix

| Predicted \ Ground Truth | RAG | SQL | HYBRID |
|---|---|---|---|
| RAG | 20 | 0 | 0 |
| SQL | 0 | 20 | 0 |
| HYBRID | 2 | 0 | 18 |

## Error Analysis - V2 Misclassifications

| Query | Ground Truth | Predicted | Confidence | Method |
|---|---|---|---|---|
| Masan có những sản phẩm chính nào và danh mục nào ... | HYBRID | RAG | 0.99 | Rule-based |
| Kế hoạch mở rộng thị trường của FPT là gì và tính ... | HYBRID | RAG | 0.99 | Rule-based |

---

## Key Findings

1. **Accuracy Improvement:** V2 achieves 96.67% vs V1's 91.67%
2. **LLM Efficiency:** Only 8.3% of queries require LLM calls, reducing latency for 55 high-confidence queries
3. **HYBRID Detection:** V2 correctly identifies HYBRID queries at 90.00% accuracy
4. **Latency Trade-off:** V2 latency is 1149.3ms (LLM calls add 1149.3ms)
