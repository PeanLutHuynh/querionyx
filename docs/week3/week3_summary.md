# Week 3 Summary - Querionyx V1 Baselines

## Chunking Strategy Decision (V1 Baseline)

Although three chunking strategies (Fixed-size, Recursive Splitting, Semantic Chunking) were explored in Week 2, only **Recursive Splitting** was selected for the RAG V1 baseline.

This decision was made based on preliminary observations:

- Better structural alignment with document sections (paragraph → sentence hierarchy)
- More stable retrieval behavior during initial experiments
- Simpler and more reproducible setup for baseline evaluation

Other strategies (Fixed-size and Semantic Chunking) are **not discarded**, but deferred to Week 4 as part of the RAG V2 upgrade (Hybrid Search + improved chunking).

Therefore, RAG V1 results should be interpreted as a **controlled baseline using a single chunking strategy**, rather than a comparative study across chunking methods.

## 1. RAG V1 Baseline Results

RAG V1 was evaluated as an offline retrieval baseline using ChromaDB cosine retrieval with `top_k=5`. The automatic evaluation used 20 unstructured annual-report questions; the first 10 were scored with embedding-based Context Precision and Context Recall.

Important interpretation note: these scores are proxy metrics based on embedding similarity, not human relevance labels. Context Precision is saturated across all tested thresholds (`0.5-0.7`) and therefore cannot serve as a reliable discriminative metric for this evaluation setup. It is retained only as a diagnostic proxy, not as a primary evaluation metric. Future evaluation will prioritize Context Recall, hard negative tests, and human evaluation, rather than relying on Context Precision.

| Metric | Value |
|---|---:|
| Average Context Precision | 1.000 |
| Average Context Recall | 0.635 |
| Average Retrieval Latency | 74.02 ms |

| question_id | Context Precision | Context Recall | Retrieved Sources |
|---|---:|---:|---|
| RAG-V1-001 | 1.000 | 0.699 | [fpt_2025.pdf - Page 101]; [fpt_2023.pdf - Page 85]; [fpt_2025.pdf - Page 77]; [fpt_2024.pdf - Page 50]; [fpt_2025.pdf - Page 80] |
| RAG-V1-002 | 1.000 | 0.750 | [vinamilk_2025.pdf - Page 45]; [vinamilk_2024.pdf - Page 49]; [vinamilk_2025.pdf - Page 49]; [vinamilk_2025.pdf - Page 3]; [vinamilk_2023.pdf - Page 8] |
| RAG-V1-003 | 1.000 | 0.580 | [masan_2023.pdf - Page 63]; [masan_2024.pdf - Page 48]; [masan_2024.pdf - Page 43]; [masan_2024.pdf - Page 67]; [masan_2023.pdf - Page 47] |
| RAG-V1-004 | 1.000 | 0.605 | [fpt_2025.pdf - Page 80]; [fpt_2025.pdf - Page 65]; [fpt_2025.pdf - Page 77]; [fpt_2025.pdf - Page 111]; [fpt_2025.pdf - Page 151] |
| RAG-V1-005 | 1.000 | 0.846 | [vinamilk_2024.pdf - Page 46]; [vinamilk_2024.pdf - Page 49]; [vinamilk_2024.pdf - Page 41]; [vinamilk_2023.pdf - Page 8]; [vinamilk_2025.pdf - Page 42] |
| RAG-V1-006 | 1.000 | 0.567 | [masan_2024.pdf - Page 44]; [masan_2024.pdf - Page 35]; [masan_2024.pdf - Page 23]; [fpt_2025.pdf - Page 143] |
| RAG-V1-007 | 1.000 | 0.570 | [fpt_2025.pdf - Page 111]; [fpt_2023.pdf - Page 56]; [fpt_2024.pdf - Page 104]; [fpt_2025.pdf - Page 104]; [fpt_2023.pdf - Page 65] |
| RAG-V1-008 | 1.000 | 0.747 | [vinamilk_2025.pdf - Page 95]; [vinamilk_2024.pdf - Page 82]; [vinamilk_2024.pdf - Page 81]; [vinamilk_2025.pdf - Page 94]; [vinamilk_2023.pdf - Page 101] |
| RAG-V1-009 | 1.000 | 0.451 | [masan_2023.pdf - Page 28]; [fpt_2025.pdf - Page 53]; [masan_2023.pdf - Page 27]; [fpt_2025.pdf - Page 44]; [fpt_2025.pdf - Page 45] |
| RAG-V1-010 | 1.000 | 0.533 | [fpt_2024.pdf - Page 10]; [fpt_2025.pdf - Page 77]; [fpt_2023.pdf - Page 43]; [fpt_2023.pdf - Page 85]; [fpt_2025.pdf - Page 60] |

## Limitations of V1 Evaluation

- Context Precision is saturated and not discriminative for the current evaluation setup.
- Context Recall is embedding-based and does not fully capture answer completeness.
- No end-to-end answer correctness metric is included in automatic evaluation.
- RAG generation is not fully evaluated due to local LLM latency constraints.

Therefore, Week 3 results should be interpreted as **retrieval baseline diagnostics**, not full QA system evaluation.

## 2. Router V1 Baseline Results

Rule-based Router V1 was evaluated on 60 labeled queries: 20 UNSTRUCTURED, 20 STRUCTURED, and 20 HYBRID.

| Metric | Value |
|---|---:|
| UNSTRUCTURED Accuracy | 100.00% |
| STRUCTURED Accuracy | 100.00% |
| HYBRID Accuracy | 75.00% |
| Overall Accuracy | 91.67% |
| Average Latency | 0.017 ms |

Confusion matrix:

| Actual Intent | Predicted RAG | Predicted SQL | Predicted HYBRID |
|---|---:|---:|---:|
| RAG | 20 | 0 | 0 |
| SQL | 0 | 20 | 0 |
| HYBRID | 5 | 0 | 15 |

## 3. Rule-Based Router Error Analysis

The router produced 5 incorrect predictions. All errors are HYBRID queries misclassified as RAG, meaning the rule-based system failed to recognize the structured SQL part of a mixed question.

Top false positives for RAG:

| Case | Question | Expected | Predicted | Explanation |
|---|---|---|---|---|
| hyb_005 | Vinamilk mô tả lợi thế cạnh tranh thế nào và danh mục nào có nhiều sản phẩm nhất? | HYBRID | RAG | The annual-report phrase "mô tả" matched RAG, but the database phrase "danh mục nào có nhiều sản phẩm nhất" was not captured strongly enough as SQL. |
| hyb_007 | Kế hoạch tăng trưởng của FPT là gì và nhân viên nào xử lý nhiều đơn hàng nhất? | HYBRID | RAG | RAG keywords "kế hoạch" and "là gì" dominated; the employee/order aggregation pattern was missed. |
| hyb_017 | Chính sách phát triển nhân sự của Vinamilk ra sao và nhân viên nào kinh doanh giỏi nhất? | HYBRID | RAG | "Chính sách" triggered RAG; "nhân viên nào kinh doanh giỏi nhất" needs SQL-style ranking but was not covered by the keyword set. |
| hyb_018 | Masan có những sản phẩm chính nào và danh mục nào có ít sản phẩm nhất? | HYBRID | RAG | No keyword matched, so the router used its safe default to RAG. This reveals a coverage gap for product/category ranking language. |
| hyb_019 | Kế hoạch mở rộng thị trường của FPT là gì và tính toàn bộ chi phí vận chuyển? | HYBRID | RAG | "Kế hoạch" and "là gì" triggered RAG; "tính toàn bộ chi phí vận chuyển" should trigger SQL aggregation but is not represented clearly enough. |

Top false negatives for HYBRID:

| Case | Question | Expected | Predicted | Explanation |
|---|---|---|---|---|
| hyb_005 | Vinamilk mô tả lợi thế cạnh tranh thế nào và danh mục nào có nhiều sản phẩm nhất? | HYBRID | RAG | HYBRID was missed because only the document-side keyword was detected. |
| hyb_007 | Kế hoạch tăng trưởng của FPT là gì và nhân viên nào xử lý nhiều đơn hàng nhất? | HYBRID | RAG | HYBRID was missed because personnel/order analytics were not modeled as SQL intent. |
| hyb_017 | Chính sách phát triển nhân sự của Vinamilk ra sao và nhân viên nào kinh doanh giỏi nhất? | HYBRID | RAG | HYBRID was missed because "kinh doanh giỏi nhất" is a semantic ranking request not covered by current SQL keywords. |
| hyb_018 | Masan có những sản phẩm chính nào và danh mục nào có ít sản phẩm nhất? | HYBRID | RAG | HYBRID was missed due to both sparse keyword coverage and the router's default-to-RAG behavior. |
| hyb_019 | Kế hoạch mở rộng thị trường của FPT là gì và tính toàn bộ chi phí vận chuyển? | HYBRID | RAG | HYBRID was missed because the SQL part uses "tính toàn bộ" instead of a currently matched aggregation phrase. |

There were no false negatives for the RAG or SQL classes in this evaluation set. The primary router weakness is HYBRID detection.

## 4. Key Observations And V2 Implications

1. RAG V1 is stable enough as a local-first baseline. The ChromaDB collection `querionyx_v1` is persisted and loadable, and retrieval latency is acceptable for V1.

2. RAG Context Precision needs a stricter diagnostic pass. The current `1.000` score is mathematically correct under the current embedding-threshold metric, but sensitivity checks at thresholds `0.5`, `0.6`, and `0.7` all remain saturated at `1.000`. Manual inspection also shows some retrieved sources cross company/year boundaries. V2 evaluation should include hard negatives, query-type grouping, per-chunk similarity logs, and more discriminative thresholds or human labels.

3. RAG Context Recall is moderate (`0.635`). This suggests the retrieved top-5 chunks often contain relevant evidence, but may not cover the full expected answer. A concrete failure case is `RAG-V1-009`, where a Masan strategy question retrieved mixed Masan and FPT context and produced recall `0.451`. This case demonstrates semantic drift in dense retrieval, where semantically similar but contextually incorrect documents (for example, different companies) are retrieved. This highlights the limitation of dense-only retrieval and motivates Hybrid Search in V2.

4. The multilingual embedding decision should be retained. The corpus and user queries are Vietnamese/English mixed, so multilingual retrieval is more appropriate than an English-only embedding baseline. For thesis reporting, `all-MiniLM-L6-v2` can be described as a comparison baseline, while `paraphrase-multilingual-MiniLM-L12-v2` is the primary V1 implementation.

5. Router V1 is strong for clear RAG and SQL questions but weaker for HYBRID. Although rule-based routing cannot truly reason over hybrid intent, it still reaches `75.00%` HYBRID accuracy when explicit SQL keywords are present. Failures consistently occur when SQL intent is implicit, confirming the limitation of keyword-based routing. V2 should improve this by detecting multiple sub-intents, expanding SQL semantic patterns, and routing mixed queries to both RAG and Text-to-SQL branches.

6. End-to-end V1 is intentionally partial. RAG branch is implemented; SQL and HYBRID branches should fail gracefully until Text-to-SQL and Hybrid orchestration are implemented in Week 4.

## Week 4 Preparation Checklist

| Item | Status | Evidence |
|---|---|---|
| ChromaDB collection `querionyx_v1` saved and loadable | Confirmed | Collection count: 9670 chunks |
| Router test queries include labels | Confirmed | `router_eval_60.json`: 60/60 queries have `ground_truth_intent`; distribution is 20 RAG, 20 SQL, 20 HYBRID |
| Ollama `qwen2.5:3b` local response | Confirmed with caveat | Short prompts respond quickly (~2-3s); full RAG prompts complete within 90s timeout with efficient context |
| Week 3 validation audit | Confirmed | See `docs/week3/week3_validation_audit.md` for embedding, metric, router, hard-negative, and Ollama checks |
