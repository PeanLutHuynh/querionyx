# RAG V1 Baseline Evaluation

## Setup

- **Pipeline:** `src/rag/rag_v1.py`
- **Retrieval:** ChromaDB cosine similarity, top_k=5
- **Evaluation model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Context precision threshold:** `0.5`
- **Questions:** 20 total; first 10 used for automatic Context Precision/Recall
- **LLM judge:** Not used
- **Manual scoring:** 1-5 scale with two annotators

## Summary

| Metric | Value |
|---|---:|
| Average Context Precision | 1.000 |
| Average Context Recall | 0.635 |
| Average Retrieval Latency | 59.02 ms |

## Automatic Evaluation Results

| question_id | question | context_precision | context_recall | retrieved_sources |
|---|---|---:|---:|---|
| RAG-V1-001 | Chiến lược kinh doanh chính của FPT trong năm 2024 là gì? | 1.000 | 0.699 | [fpt_2025.pdf - Page 101]; [fpt_2023.pdf - Page 85]; [fpt_2025.pdf - Page 77]; [fpt_2024.pdf - Page 50]; [fpt_2025.pdf - Page 80] |
| RAG-V1-002 | Vinamilk đã đạt được những mục tiêu gì trong báo cáo thường niên 2023? | 1.000 | 0.750 | [vinamilk_2025.pdf - Page 45]; [vinamilk_2024.pdf - Page 49]; [vinamilk_2025.pdf - Page 49]; [vinamilk_2025.pdf - Page 3]; [vinamilk_2023.pdf - Page 8] |
| RAG-V1-003 | Masan Group mô tả rủi ro kinh doanh nào trong năm 2024? | 1.000 | 0.580 | [masan_2023.pdf - Page 63]; [masan_2024.pdf - Page 48]; [masan_2024.pdf - Page 43]; [masan_2024.pdf - Page 67]; [masan_2023.pdf - Page 47] |
| RAG-V1-004 | FPT có những mảng kinh doanh chính nào được đề cập trong báo cáo 2025? | 1.000 | 0.605 | [fpt_2025.pdf - Page 80]; [fpt_2025.pdf - Page 65]; [fpt_2025.pdf - Page 77]; [fpt_2025.pdf - Page 111]; [fpt_2025.pdf - Page 151] |
| RAG-V1-005 | Vinamilk báo cáo doanh thu xuất khẩu như thế nào trong năm 2024? | 1.000 | 0.846 | [vinamilk_2024.pdf - Page 46]; [vinamilk_2024.pdf - Page 49]; [vinamilk_2024.pdf - Page 41]; [vinamilk_2023.pdf - Page 8]; [vinamilk_2025.pdf - Page 42] |
| RAG-V1-006 | Masan trình bày định hướng phát triển hệ sinh thái tiêu dùng trong năm 2023 ra sao? | 1.000 | 0.567 | [masan_2024.pdf - Page 44]; [masan_2024.pdf - Page 35]; [masan_2024.pdf - Page 23]; [fpt_2025.pdf - Page 143] |
| RAG-V1-007 | Báo cáo thường niên 2023 của FPT nhấn mạnh vai trò của chuyển đổi số như thế nào? | 1.000 | 0.570 | [fpt_2025.pdf - Page 111]; [fpt_2023.pdf - Page 56]; [fpt_2024.pdf - Page 104]; [fpt_2025.pdf - Page 104]; [fpt_2023.pdf - Page 65] |
| RAG-V1-008 | Vinamilk mô tả hệ thống quản lý rủi ro trong năm 2025 như thế nào? | 1.000 | 0.747 | [vinamilk_2025.pdf - Page 95]; [vinamilk_2024.pdf - Page 82]; [vinamilk_2024.pdf - Page 81]; [vinamilk_2025.pdf - Page 94]; [vinamilk_2023.pdf - Page 101] |
| RAG-V1-009 | Masan đề cập những ưu tiên chiến lược nào cho năm 2025? | 1.000 | 0.451 | [masan_2023.pdf - Page 28]; [fpt_2025.pdf - Page 53]; [masan_2023.pdf - Page 27]; [fpt_2025.pdf - Page 44]; [fpt_2025.pdf - Page 45] |
| RAG-V1-010 | FPT báo cáo kết quả kinh doanh mảng công nghệ năm 2024 như thế nào? | 1.000 | 0.533 | [fpt_2024.pdf - Page 10]; [fpt_2025.pdf - Page 77]; [fpt_2023.pdf - Page 43]; [fpt_2023.pdf - Page 85]; [fpt_2025.pdf - Page 60] |

## Manual Scoring Protocol

Manual scores should be filled in `docs/evaluation/manual_eval_template.csv` independently by two annotators.

| Score | Meaning |
|---:|---|
| 1 | Completely wrong or unsupported |
| 2 | Mostly wrong, minimal useful evidence |
| 3 | Partially correct, incomplete or weakly sourced |
| 4 | Mostly correct and reasonably sourced |
| 5 | Fully correct, concise, and well-sourced |

## Notes

- Context Precision and Recall are embedding-similarity proxies, not human relevance judgments.
- The evaluation model is aligned with the current multilingual RAG index for bilingual retrieval consistency.
- To populate `rag_answer` with local Ollama outputs, run:

```powershell
$env:EVAL_RAG_GENERATE_ANSWERS='1'; .venv\Scripts\python.exe src\evaluation\eval_rag_v1.py
```
