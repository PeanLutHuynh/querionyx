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
| Avg Latency | 0.017 ms |
| P95 Latency | 0.021 ms |

## V2 (LLM-based) Summary

| Metric | Value |
|---|---|
| Overall Accuracy | 91.67% |
| RAG Accuracy | 100.00% |
| SQL Accuracy | 100.00% |
| HYBRID Accuracy | 75.00% |
| Avg Latency | 2328.438 ms |
| P95 Latency | 6791.440 ms |
| LLM Call Rate | 25.00% |
| Rule-based Skips | 45 / 60 |

## V1 vs V2 Comparison

| Metric | V1 | V2 | Change |
|---|---|---|---|
| Overall Accuracy | 91.67% | 91.67% | +0.00% |
| RAG Accuracy | 100.00% | 100.00% | +0.00% |
| SQL Accuracy | 100.00% | 100.00% | +0.00% |
| HYBRID Accuracy | 75.00% | 75.00% | +0.00% |
| Avg Latency (ms) | 0.02 | 2328.44 | +2328.42 |

## V2 Efficiency Analysis

- **LLM Calls:** 15 / 60 (25.0%)
- **Rule-based Shortcuts:** 45 queries skipped LLM (direct rule-based)
- **Efficiency Gain:** 75.0% reduction in LLM calls vs full LLM classification

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
| HYBRID | 5 | 0 | 15 |

## Error Analysis - V2 Misclassifications

| Query | Ground Truth | Predicted | Confidence | Method |
|---|---|---|---|---|
| Vinamilk mô tả lợi thế cạnh tranh thế nào và danh ... | HYBRID | RAG | 0.99 | Rule-based |
| Kế hoạch tăng trưởng của FPT là gì và nhân viên nà... | HYBRID | RAG | 0.99 | Rule-based |
| Chính sách phát triển nhân sự của Vinamilk ra sao ... | HYBRID | RAG | 0.99 | Rule-based |
| Masan có những sản phẩm chính nào và danh mục nào ... | HYBRID | RAG | 0.99 | Rule-based |
| Kế hoạch mở rộng thị trường của FPT là gì và tính ... | HYBRID | RAG | 0.99 | Rule-based |

---

## Key Findings

1. **Accuracy Improvement:** V2 achieves 91.67% vs V1's 91.67%
2. **LLM Efficiency:** Only 25.0% of queries require LLM calls, reducing latency for 45 high-confidence queries
3. **HYBRID Detection:** V2 correctly identifies HYBRID queries at 75.00% accuracy
4. **Latency Trade-off:** V2 latency is 2328.4ms (LLM calls add 2328.4ms)
