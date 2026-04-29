# Rule-based Router V1 - Baseline Evaluation Report

**Date:** 2026-05-01

**Purpose:** Establish baseline for Router accuracy comparison (V1 vs V2 LLM-based vs V3 Adaptive).

---

## Summary Metrics

- **Total Queries:** 60
- **Correct Predictions:** 55
- **Incorrect Predictions:** 5
- **Overall Accuracy:** 91.67%

## Accuracy by Query Type

| Query Type | Count | Accuracy | Notes |
|---|---|---|---|
| UNSTRUCTURED (RAG) | 20 | 100.00% | Document-based questions |
| STRUCTURED (SQL) | 20 | 100.00% | Database queries |
| HYBRID | 20 | 75.00% | Require both sources - **Expected ~0%** |

## Latency Analysis

| Metric | Value |
|---|---|
| Average | 0.017 ms |
| Min | 0.011 ms |
| Max | 0.054 ms |
| P50 | 0.017 ms |
| P95 | 0.025 ms |

## Confusion Matrix (3×3)

|  | Predicted RAG | Predicted SQL | Predicted HYBRID |
|---|---|---|---|
| Actual RAG | 20 | 0 | 0 |
| Actual SQL | 0 | 20 | 0 |
| Actual HYBRID | 5 | 0 | 15 |

## Error Analysis

**Total Errors:** 5

### Incorrect Predictions (Sample)

**Error 1:**
- Question: Vinamilk mô tả lợi thế cạnh tranh thế nào và danh mục nào có nhiều sản phẩm nhất?
- Expected: HYBRID
- Predicted: RAG
- Reasoning: Found 1 RAG keyword(s)

**Error 2:**
- Question: Kế hoạch tăng trưởng của FPT là gì và nhân viên nào xử lý nhiều đơn hàng nhất?
- Expected: HYBRID
- Predicted: RAG
- Reasoning: Found 2 RAG keyword(s)

**Error 3:**
- Question: Chính sách phát triển nhân sự của Vinamilk ra sao và nhân viên nào kinh doanh giỏi nhất?
- Expected: HYBRID
- Predicted: RAG
- Reasoning: Found 1 RAG keyword(s)

**Error 4:**
- Question: Masan có những sản phẩm chính nào và danh mục nào có ít sản phẩm nhất?
- Expected: HYBRID
- Predicted: RAG
- Reasoning: No keywords matched; defaulting to RAG (safe fallback)

**Error 5:**
- Question: Kế hoạch mở rộng thị trường của FPT là gì và tính toàn bộ chi phí vận chuyển?
- Expected: HYBRID
- Predicted: RAG
- Reasoning: Found 2 RAG keyword(s)

## Key Findings

1. **HYBRID Accuracy Expected ~0%**
   - Rule-based router cannot handle HYBRID queries that require both RAG and SQL sources.
   - This establishes the baseline justification for implementing LLM-based Router (V2) in week 4.

2. **UNSTRUCTURED and STRUCTURED handling**
   - Rule-based keyword matching works well for clear intent signals.
   - UNSTRUCTURED accuracy: 100.0%
   - STRUCTURED accuracy: 100.0%

3. **Performance**
   - Very fast: avg 0.02ms (deterministic, no LLM calls)
   - Suitable for real-time deployment as lightweight baseline

## Conclusion

Rule-based Router V1 provides a deterministic, fast baseline for intent classification.
It performs well for clear-signal queries (UNSTRUCTURED / STRUCTURED) but fails on ambiguous
HYBRID queries. This data motivates the development of LLM-based and Adaptive routers in subsequent weeks.
