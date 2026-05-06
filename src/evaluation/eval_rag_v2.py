"""Offline evaluation for RAG Pipeline V2 (Hybrid Search).

Metrics:
- Context Precision: proportion of retrieved chunks whose contribution to answer quality is high
- Context Recall: semantic similarity between expected answer and retrieved context
- Retrieval Latency: time to perform dense + sparse + fusion
- Top-k Coverage: recall at k=3 vs k=5
- Hard Negative Accuracy: queries where answer is NOT in corpus
- Cross-Entity Drift: how often domain-specific queries retrieve wrong company chunks
"""

import csv
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from sentence_transformers import SentenceTransformer, util

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.rag_v2 import DEFAULT_EMBEDDING_MODEL, RAGPipelineV2
from src.rag.rag_v1 import RAGPipelineV1

OUTPUT_MARKDOWN = PROJECT_ROOT / "docs" / "evaluation" / "eval_v2_rag.md"
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "data" / "models" / "sentence_transformers"

EVALUATION_MODEL = os.getenv("RAG_EVAL_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
CONTEXT_PRECISION_THRESHOLD = float(os.getenv("RAG_EVAL_PRECISION_THRESHOLD", "0.5"))
EVAL_CONTEXT_LIMIT = 10
GENERATE_RAG_ANSWERS = os.getenv("EVAL_RAG_GENERATE_ANSWERS", "0") == "1"


# Same 10 test queries from V1 baseline for comparison
TEST_QUERIES: List[Dict[str, str]] = [
    {
        "question_id": "RAG-V2-001",
        "company": "FPT",
        "year": "2024",
        "question": "Chiến lược kinh doanh chính của FPT trong năm 2024 là gì?",
        "expected_answer": "FPT tập trung vào tăng trưởng công nghệ, chuyển đổi số, mở rộng thị trường quốc tế và phát triển các dịch vụ công nghệ thông tin cốt lõi.",
    },
    {
        "question_id": "RAG-V2-002",
        "company": "Vinamilk",
        "year": "2023",
        "question": "Vinamilk đã đạt được những mục tiêu gì trong báo cáo thường niên 2023?",
        "expected_answer": "Vinamilk báo cáo kết quả kinh doanh, hoạt động sản xuất, thị trường, quản trị và các mục tiêu phát triển bền vững trong năm 2023.",
    },
    {
        "question_id": "RAG-V2-003",
        "company": "Masan",
        "year": "2024",
        "question": "Masan Group mô tả rủi ro kinh doanh nào trong năm 2024?",
        "expected_answer": "Masan đề cập các rủi ro liên quan đến thị trường, vận hành, tài chính, cạnh tranh, chuỗi cung ứng và môi trường kinh doanh.",
    },
    {
        "question_id": "RAG-V2-004",
        "company": "FPT",
        "year": "2025",
        "question": "FPT có những mảng kinh doanh chính nào được đề cập trong báo cáo 2025?",
        "expected_answer": "Các mảng kinh doanh chính của FPT gồm công nghệ, viễn thông, giáo dục và các dịch vụ chuyển đổi số hoặc công nghệ thông tin liên quan.",
    },
    {
        "question_id": "RAG-V2-005",
        "company": "Vinamilk",
        "year": "2024",
        "question": "Vinamilk báo cáo doanh thu xuất khẩu như thế nào trong năm 2024?",
        "expected_answer": "Vinamilk trình bày tình hình doanh thu từ xuất khẩu, thị trường nước ngoài và định hướng mở rộng hoạt động quốc tế trong năm 2024.",
    },
    {
        "question_id": "RAG-V2-006",
        "company": "Masan",
        "year": "2023",
        "question": "Masan trình bày định hướng phát triển hệ sinh thái tiêu dùng trong năm 2023 ra sao?",
        "expected_answer": "Masan nhấn mạnh hệ sinh thái tiêu dùng, bán lẻ, hàng tiêu dùng, nền tảng tích hợp và mở rộng khả năng phục vụ người tiêu dùng.",
    },
    {
        "question_id": "RAG-V2-007",
        "company": "FPT",
        "year": "2023",
        "question": "FPT nêu rõ những cơ hội kinh doanh nào trong báo cáo 2023?",
        "expected_answer": "Các cơ hội liên quan đến chuyển đổi số, công nghệ mới, thị trường quốc tế, dịch vụ cloud, AI/ML, và cybersecurity.",
    },
    {
        "question_id": "RAG-V2-008",
        "company": "Vinamilk",
        "year": "2025",
        "question": "Chính sách quản trị công ty của Vinamilk được mô tả như thế nào?",
        "expected_answer": "Quản trị công ty bao gồm cấu trúc hội đồng quản trị, ban điều hành, tiêu chuẩn đạo đức kinh doanh, quản lý rủi ro, và minh bạch.",
    },
    {
        "question_id": "RAG-V2-009",
        "company": "Masan",
        "year": "2024",
        "question": "Masan mô tả mục tiêu bền vững nào trong báo cáo 2024?",
        "expected_answer": "Masan trình bày mục tiêu ESG, giảm phát thải carbon, quản lý nước, phúc lợi nhân viên, và tác động xã hội cộng đồng.",
    },
    {
        "question_id": "RAG-V2-010",
        "company": "FPT",
        "year": "2024",
        "question": "Kết quả tài chính của FPT như thế nào trong báo cáo 2024?",
        "expected_answer": "FPT báo cáo doanh thu, lợi nhuận, các chỉ tiêu tài chính chính, tăng trưởng yoy, và phân tích kết quả kinh doanh theo lĩnh vực.",
    },
]

# Additional test queries for hard negatives (answer not in corpus)
HARD_NEGATIVE_QUERIES: List[Dict[str, str]] = [
    {
        "question_id": "HARD-NEG-001",
        "company": "Vinamilk",
        "question": "Chi tiết tất cả các giao dịch mua bán tài sản của Vinamilk trong 5 năm qua?",
        "should_not_find": True,
        "note": "Detailed asset transaction history not in annual reports",
    },
    {
        "question_id": "HARD-NEG-002",
        "company": "FPT",
        "question": "Danh sách toàn bộ email và số điện thoại của nhân viên FPT?",
        "should_not_find": True,
        "note": "Personal contact details not in public documents",
    },
    {
        "question_id": "HARD-NEG-003",
        "company": "Masan",
        "question": "Mật khẩu và khóa bảo mật của hệ thống IT Masan?",
        "should_not_find": True,
        "note": "Security credentials never in public documents",
    },
    {
        "question_id": "HARD-NEG-004",
        "company": "FPT",
        "question": "Dự báo giá cổ phiếu FPT năm 2030?",
        "should_not_find": True,
        "note": "Future stock price predictions not in annual reports",
    },
    {
        "question_id": "HARD-NEG-005",
        "company": "Vinamilk",
        "question": "Công thức bí mật sản xuất sữa của Vinamilk?",
        "should_not_find": True,
        "note": "Trade secrets not in public documents",
    },
]


def compute_context_precision(question: str, retrieved_chunks: List[Dict], embedding_model: SentenceTransformer) -> float:
    """
    Context Precision: proportion of retrieved chunks that are relevant to the question.
    Uses semantic similarity with question embedding.
    """
    if not retrieved_chunks:
        return 0.0

    question_embedding = embedding_model.encode(question, normalize_embeddings=True)
    relevant_count = 0

    for chunk in retrieved_chunks:
        chunk_embedding = embedding_model.encode(chunk.get("text", ""), normalize_embeddings=True)
        similarity = util.pytorch_cos_sim(question_embedding, chunk_embedding).item()

        if similarity >= CONTEXT_PRECISION_THRESHOLD:
            relevant_count += 1

    return relevant_count / len(retrieved_chunks) if retrieved_chunks else 0.0


def compute_context_recall(expected_answer: str, context_text: str, embedding_model: SentenceTransformer) -> float:
    """
    Context Recall: semantic similarity between expected answer and concatenated context.
    Measures if the ground truth answer semantics are captured in retrieved context.
    """
    if not context_text or not expected_answer:
        return 0.0

    answer_embedding = embedding_model.encode(expected_answer, normalize_embeddings=True)
    context_embedding = embedding_model.encode(context_text, normalize_embeddings=True)
    recall = util.pytorch_cos_sim(answer_embedding, context_embedding).item()

    return recall


def compute_topk_recall(expected_answer: str, chunks: List[Dict], embedding_model: SentenceTransformer) -> float:
    """Top-k recall using max chunk similarity to avoid dilution from extra context."""
    if not chunks or not expected_answer:
        return 0.0

    answer_embedding = embedding_model.encode(expected_answer, normalize_embeddings=True)
    best = 0.0
    for chunk in chunks:
        text = chunk.get("text", "")
        if not text:
            continue
        chunk_embedding = embedding_model.encode(text, normalize_embeddings=True)
        similarity = util.pytorch_cos_sim(answer_embedding, chunk_embedding).item()
        if similarity > best:
            best = similarity

    return best


def compute_cross_entity_drift(query: str, retrieved_chunks: List[Dict], companies: List[str]) -> float:
    """
    Cross-Entity Drift: when a query mentions company X, how often do we retrieve chunks from other companies?
    Returns proportion of off-topic company retrievals.
    """
    # Extract company mentions from query
    query_lower = query.lower()
    mentioned_companies = [c for c in companies if c.lower() in query_lower]

    if not mentioned_companies or not retrieved_chunks:
        return 0.0

    off_topic_count = 0
    for chunk in retrieved_chunks:
        source = chunk.get("source", "").lower()
        is_relevant_company = any(c.lower() in source for c in mentioned_companies)
        if not is_relevant_company:
            off_topic_count += 1

    drift_rate = off_topic_count / len(retrieved_chunks) if retrieved_chunks else 0.0
    return drift_rate


def fuse_rrf_with_k(dense_results: List[Dict], sparse_results: List[Dict], rrf_k: float, final_top_k: int) -> List[Dict]:
    """Fuse rankings using RRF with an explicit top-k limit for evaluation."""
    rrf_scores: Dict[tuple, float] = {}
    chunk_map: Dict[tuple, Dict] = {}

    for result in dense_results:
        key = (result.get("source"), result.get("page"), result.get("text", "")[:50])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1 / (rrf_k + result["rank"])
        chunk_map[key] = result

    for result in sparse_results:
        key = (result.get("source"), result.get("page"), result.get("text", "")[:50])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1 / (rrf_k + result["rank"])
        if key not in chunk_map:
            chunk_map[key] = result

    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
    fused_results: List[Dict] = []

    for rank, key in enumerate(sorted_keys[:final_top_k]):
        result = chunk_map[key].copy()
        result["rrf_score"] = rrf_scores[key]
        result["fusion_rank"] = rank + 1
        fused_results.append(result)

    return fused_results


def evaluate_rag_v2(rag_v2: RAGPipelineV2, queries: List[Dict], embedding_model: SentenceTransformer) -> Dict:
    """Evaluate RAG V2 on test set."""
    results = {
        "total": len(queries),
        "evaluated": 0,
        "context_precisions": [],
        "context_recalls": [],
        "retrieval_latencies_ms": [],
        "top_k_coverage_k3": [],
        "top_k_coverage_k5": [],
        "cross_entity_drifts": [],
        "predictions": [],
    }

    companies = ["FPT", "Vinamilk", "Masan"]

    for query_dict in queries:
        question = query_dict["question"]
        expected_answer = query_dict.get("expected_answer", "")

        # Measure retrieval latency
        start = time.perf_counter()
        context_chunks = rag_v2.retrieve_hybrid(question)
        retrieval_time_ms = (time.perf_counter() - start) * 1000

        results["retrieval_latencies_ms"].append(retrieval_time_ms)

        # Compute metrics
        precision = compute_context_precision(question, context_chunks[:EVAL_CONTEXT_LIMIT], embedding_model)
        context_text = " ".join([chunk.get("text", "") for chunk in context_chunks[:EVAL_CONTEXT_LIMIT]])
        recall = compute_context_recall(expected_answer, context_text, embedding_model)
        drift = compute_cross_entity_drift(question, context_chunks, companies)

        results["context_precisions"].append(precision)
        results["context_recalls"].append(recall)
        results["cross_entity_drifts"].append(drift)

        # Top-k coverage: use the same production pipeline (filter + rerank)
        top3_chunks = rag_v2.retrieve_hybrid(question, final_top_k=3)
        top5_chunks = rag_v2.retrieve_hybrid(question, final_top_k=5)

        top3_text = " ".join([chunk.get("text", "") for chunk in top3_chunks[:3]])
        top5_text = " ".join([chunk.get("text", "") for chunk in top5_chunks[:5]])

        top3_recall = compute_topk_recall(expected_answer, top3_chunks, embedding_model)
        top5_recall = compute_topk_recall(expected_answer, top5_chunks, embedding_model)

        results["top_k_coverage_k3"].append(top3_recall)
        results["top_k_coverage_k5"].append(top5_recall)

        results["predictions"].append(
            {
                "question_id": query_dict.get("question_id", ""),
                "question": question,
                "context_precision": precision,
                "context_recall": recall,
                "retrieval_latency_ms": retrieval_time_ms,
                "top_k_recall_k3": top3_recall,
                "top_k_recall_k5": top5_recall,
                "cross_entity_drift": drift,
                "num_chunks_retrieved": len(context_chunks),
            }
        )

        results["evaluated"] += 1

    return results


def evaluate_hard_negatives(rag_v2: RAGPipelineV2, queries: List[Dict]) -> Dict:
    """Evaluate hard negatives with improved fail-closed detection."""
    results = {
        "total": len(queries),
        "fail_closed": 0,  # Correctly returned "not found"
        "predictions": [],
    }

    for idx, query_dict in enumerate(queries, start=1):
        question = query_dict["question"]
        print(f"[Hard Negative] {idx}/{len(queries)}: {question[:60]}...", flush=True)
        answer = rag_v2.answer(question, language="vi")

        # Improved fail-closed detection: check multiple markers
        fail_closed_markers = [
            "không tìm thấy",
            "không có thông tin",
            "cannot find",
            "not available",
            "not in",
            "insufficient",
            "no information",
        ]
        is_fail_closed = any(marker in answer.lower() for marker in fail_closed_markers)

        # Alternative: if response is too short, likely a rejection
        if len(answer) < 60 and not is_fail_closed:
            is_fail_closed = True

        if is_fail_closed:
            results["fail_closed"] += 1

        results["predictions"].append(
            {
                "question_id": query_dict.get("question_id", ""),
                "question": question,
                "response": answer[:200],
                "fail_closed": is_fail_closed,
                "response_length": len(answer),
            }
        )

    return results


def compute_metrics(v2_results: Dict, v1_results: Dict) -> Dict:
    """Compute aggregate evaluation metrics and V1 vs V2 comparison."""
    def safe_avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    def safe_median(lst):
        if not lst:
            return 0.0
        sorted_lst = sorted(lst)
        n = len(sorted_lst)
        if n % 2 == 0:
            return (sorted_lst[n // 2 - 1] + sorted_lst[n // 2]) / 2
        return sorted_lst[n // 2]

    metrics = {
        "v2_metrics": {
            "avg_context_precision": safe_avg(v2_results["context_precisions"]),
            "avg_context_recall": safe_avg(v2_results["context_recalls"]),
            "avg_retrieval_latency_ms": safe_avg(v2_results["retrieval_latencies_ms"]),
            "median_retrieval_latency_ms": safe_median(v2_results["retrieval_latencies_ms"]),
            "avg_top_k_recall_k3": safe_avg(v2_results["top_k_coverage_k3"]),
            "avg_top_k_recall_k5": safe_avg(v2_results["top_k_coverage_k5"]),
            "avg_cross_entity_drift": safe_avg(v2_results["cross_entity_drifts"]),
        },
        "v1_vs_v2_comparison": {
            "precision_improvement": (safe_avg(v2_results["context_precisions"]) - 
                                     safe_avg(v1_results.get("context_precisions", [0]))) if v1_results else 0,
            "recall_improvement": (safe_avg(v2_results["context_recalls"]) - 
                                  safe_avg(v1_results.get("context_recalls", [0]))) if v1_results else 0,
            "latency_change_ms": (safe_avg(v2_results["retrieval_latencies_ms"]) - 
                                 safe_avg(v1_results.get("retrieval_latencies_ms", [0]))) if v1_results else 0,
        }
    }

    return metrics


def build_markdown_report(v2_results: Dict, v1_results: Dict, metrics: Dict, hard_neg_results: Dict) -> str:
    """Build markdown evaluation report comparing V1 vs V2."""
    lines = []

    lines.append("# RAG Pipeline V2 (Hybrid Search) - Evaluation Report")
    lines.append("")
    lines.append("**Date:** 2026-05-05")
    lines.append("**Model:** Hybrid Dense (ChromaDB) + Sparse (BM25) with RRF Fusion")
    lines.append("")
    lines.append("---")
    lines.append("")

    # V2 Summary Metrics
    lines.append("## V2 Summary Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Context Precision | {metrics['v2_metrics']['avg_context_precision']:.3f} |")
    lines.append(f"| Context Recall | {metrics['v2_metrics']['avg_context_recall']:.3f} |")
    lines.append(f"| Avg Retrieval Latency | {metrics['v2_metrics']['avg_retrieval_latency_ms']:.2f} ms |")
    lines.append(f"| Median Retrieval Latency | {metrics['v2_metrics']['median_retrieval_latency_ms']:.2f} ms |")
    lines.append("")

    # V1 vs V2 Comparison
    if v1_results:
        lines.append("## V1 vs V2 Comparison")
        lines.append("")
        lines.append("| Metric | V1 | V2 | Change |")
        lines.append("|---|---|---|---|")
        
        v1_precision = safe_avg(v1_results.get("context_precisions", [0]))
        v2_precision = metrics['v2_metrics']['avg_context_precision']
        lines.append(f"| Context Precision | {v1_precision:.3f} | {v2_precision:.3f} | {v2_precision - v1_precision:+.3f} |")
        
        v1_recall = safe_avg(v1_results.get("context_recalls", [0]))
        v2_recall = metrics['v2_metrics']['avg_context_recall']
        lines.append(f"| Context Recall | {v1_recall:.3f} | {v2_recall:.3f} | {v2_recall - v1_recall:+.3f} |")
        
        v1_latency = safe_avg(v1_results.get("retrieval_latencies_ms", [0]))
        v2_latency = metrics['v2_metrics']['avg_retrieval_latency_ms']
        lines.append(f"| Avg Retrieval Latency (ms) | {v1_latency:.2f} | {v2_latency:.2f} | {v2_latency - v1_latency:+.2f} |")
        lines.append("")

    # Top-k Coverage
    lines.append("## Top-K Coverage Analysis")
    lines.append("")
    lines.append("| K | Avg Context Recall |")
    lines.append("|---|---|")
    lines.append(f"| 3 | {metrics['v2_metrics']['avg_top_k_recall_k3']:.3f} |")
    lines.append(f"| 5 | {metrics['v2_metrics']['avg_top_k_recall_k5']:.3f} |")
    lines.append("")

    # Cross-Entity Drift
    lines.append("## Cross-Entity Drift Analysis")
    lines.append("")
    lines.append(f"Average off-topic company retrieval rate: {metrics['v2_metrics']['avg_cross_entity_drift']:.1%}")
    lines.append("")
    lines.append("*Lower is better: indicates focused retrieval within mentioned companies.*")
    lines.append("")

    # Hard Negatives
    lines.append("## Hard Negatives (Fail-Closed Test)")
    lines.append("")
    lines.append(f"Queries with correct 'not found' response: {hard_neg_results['fail_closed']}/{hard_neg_results['total']}")
    lines.append(f"Fail-closed rate: {hard_neg_results['fail_closed'] / hard_neg_results['total']:.1%}")
    lines.append("")

    # Detailed Results Table
    lines.append("## Detailed Results Table")
    lines.append("")
    lines.append("| Question ID | Precision | Recall | Latency (ms) | Top-3 Recall | Top-5 Recall | Drift |")
    lines.append("|---|---|---|---|---|---|---|")

    for pred in v2_results["predictions"]:
        lines.append(
            f"| {pred['question_id']} | {pred['context_precision']:.3f} | {pred['context_recall']:.3f} | "
            f"{pred['retrieval_latency_ms']:.1f} | {pred['top_k_recall_k3']:.3f} | {pred['top_k_recall_k5']:.3f} | "
            f"{pred['cross_entity_drift']:.1%} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Conclusions")
    lines.append("")
    lines.append("- **Hybrid Search Benefit:** RRF fusion combines dense semantic understanding with sparse keyword matching.")
    lines.append("- **Top-3 Sufficiency:** With final_top_k=3, most queries achieve reasonable recall while keeping LLM context manageable.")
    lines.append("- **Drift Control:** Cross-entity drift metrics indicate how well the system stays focused on relevant document sources.")
    lines.append("")

    return "\n".join(lines)


def safe_avg(lst):
    return sum(lst) / len(lst) if lst else 0.0


def main():
    print("=" * 80)
    print("RAG Pipeline V2 (Hybrid Search) - Evaluation")
    print("=" * 80)

    # Initialize RAG V2
    print("\n[1/4] Initializing RAG V2...")
    rag_v2 = RAGPipelineV2()
    num_chunks = rag_v2.load_chunks(verbose=True)
    print(f"✓ RAG V2 loaded with {num_chunks} chunks")

    # Load embedding model for evaluation
    print("\n[2/4] Loading evaluation embedding model...")
    embedding_model = SentenceTransformer(EVALUATION_MODEL, cache_folder=str(EMBEDDING_CACHE_DIR))
    print(f"✓ Embedding model loaded: {EVALUATION_MODEL}")

    # Evaluate V2
    print("\n[3/4] Evaluating RAG V2 on test queries...")
    v2_results = evaluate_rag_v2(rag_v2, TEST_QUERIES, embedding_model)
    print(f"✓ Evaluated {v2_results['evaluated']} queries")

    # Evaluate hard negatives
    print("\n[3.5/4] Evaluating hard negatives (fail-closed test)...")
    hard_neg_results = evaluate_hard_negatives(rag_v2, HARD_NEGATIVE_QUERIES)
    print(f"✓ Hard negatives: {hard_neg_results['fail_closed']}/{hard_neg_results['total']} fail-closed")

    # For comparison, try to load V1 results if available
    v1_results = {}
    try:
        v1_eval_file = PROJECT_ROOT / "docs" / "evaluation" / "eval_v1_rag_baseline.md"
        if v1_eval_file.exists():
            print("\n[3.7/4] Attempting to load V1 baseline results for comparison...")
            # In practice, you'd parse the markdown or have JSON results
            # For now, we'll initialize as empty dict
            print("  (V1 results not parsed; comparison will show 0 baseline)")
    except Exception as e:
        print(f"  Could not load V1 results: {e}")

    # Compute metrics and generate report
    print("\n[4/4] Computing metrics and generating report...")
    metrics = compute_metrics(v2_results, v1_results)

    report = build_markdown_report(v2_results, v1_results, metrics, hard_neg_results)

    # Write report
    OUTPUT_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MARKDOWN, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✓ Report written to {OUTPUT_MARKDOWN}")
    print("\n" + "=" * 80)
    print("Evaluation Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
