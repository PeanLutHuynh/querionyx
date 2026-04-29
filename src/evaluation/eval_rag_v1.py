"""Offline evaluation setup for RAG Pipeline V1.

Metrics:
- Context Precision: proportion of retrieved chunks whose cosine similarity
  with the question is above a relevance threshold.
- Context Recall: cosine similarity between the expected answer and the
  concatenated retrieved context.

This script intentionally avoids LLM-as-judge evaluation. It can optionally
generate RAG answers for the manual scoring template with local Ollama by
setting EVAL_RAG_GENERATE_ANSWERS=1.
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

from src.rag.rag_v1 import DEFAULT_EMBEDDING_MODEL, RAGPipelineV1

OUTPUT_MARKDOWN = PROJECT_ROOT / "docs" / "evaluation" / "eval_v1_rag_baseline.md"
MANUAL_TEMPLATE = PROJECT_ROOT / "docs" / "evaluation" / "manual_eval_template.csv"
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "data" / "models" / "sentence_transformers"

EVALUATION_MODEL = os.getenv("RAG_EVAL_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
CONTEXT_PRECISION_THRESHOLD = float(os.getenv("RAG_EVAL_PRECISION_THRESHOLD", "0.5"))
EVAL_CONTEXT_LIMIT = 10
GENERATE_RAG_ANSWERS = os.getenv("EVAL_RAG_GENERATE_ANSWERS", "0") == "1"


TEST_QUERIES: List[Dict[str, str]] = [
    {
        "question_id": "RAG-V1-001",
        "company": "FPT",
        "year": "2024",
        "question": "Chiến lược kinh doanh chính của FPT trong năm 2024 là gì?",
        "expected_answer": "FPT tập trung vào tăng trưởng công nghệ, chuyển đổi số, mở rộng thị trường quốc tế và phát triển các dịch vụ công nghệ thông tin cốt lõi.",
    },
    {
        "question_id": "RAG-V1-002",
        "company": "Vinamilk",
        "year": "2023",
        "question": "Vinamilk đã đạt được những mục tiêu gì trong báo cáo thường niên 2023?",
        "expected_answer": "Vinamilk báo cáo kết quả kinh doanh, hoạt động sản xuất, thị trường, quản trị và các mục tiêu phát triển bền vững trong năm 2023.",
    },
    {
        "question_id": "RAG-V1-003",
        "company": "Masan",
        "year": "2024",
        "question": "Masan Group mô tả rủi ro kinh doanh nào trong năm 2024?",
        "expected_answer": "Masan đề cập các rủi ro liên quan đến thị trường, vận hành, tài chính, cạnh tranh, chuỗi cung ứng và môi trường kinh doanh.",
    },
    {
        "question_id": "RAG-V1-004",
        "company": "FPT",
        "year": "2025",
        "question": "FPT có những mảng kinh doanh chính nào được đề cập trong báo cáo 2025?",
        "expected_answer": "Các mảng kinh doanh chính của FPT gồm công nghệ, viễn thông, giáo dục và các dịch vụ chuyển đổi số hoặc công nghệ thông tin liên quan.",
    },
    {
        "question_id": "RAG-V1-005",
        "company": "Vinamilk",
        "year": "2024",
        "question": "Vinamilk báo cáo doanh thu xuất khẩu như thế nào trong năm 2024?",
        "expected_answer": "Vinamilk trình bày tình hình doanh thu từ xuất khẩu, thị trường nước ngoài và định hướng mở rộng hoạt động quốc tế trong năm 2024.",
    },
    {
        "question_id": "RAG-V1-006",
        "company": "Masan",
        "year": "2023",
        "question": "Masan trình bày định hướng phát triển hệ sinh thái tiêu dùng trong năm 2023 ra sao?",
        "expected_answer": "Masan nhấn mạnh hệ sinh thái tiêu dùng, bán lẻ, hàng tiêu dùng, nền tảng tích hợp và mở rộng khả năng phục vụ người tiêu dùng.",
    },
    {
        "question_id": "RAG-V1-007",
        "company": "FPT",
        "year": "2023",
        "question": "Báo cáo thường niên 2023 của FPT nhấn mạnh vai trò của chuyển đổi số như thế nào?",
        "expected_answer": "FPT xem chuyển đổi số là động lực tăng trưởng, gắn với dịch vụ công nghệ, tư vấn, triển khai giải pháp số và năng lực cạnh tranh.",
    },
    {
        "question_id": "RAG-V1-008",
        "company": "Vinamilk",
        "year": "2025",
        "question": "Vinamilk mô tả hệ thống quản lý rủi ro trong năm 2025 như thế nào?",
        "expected_answer": "Vinamilk vận hành hệ thống quản lý rủi ro thường xuyên, gồm nhận diện, đánh giá, giám sát và báo cáo rủi ro trong toàn công ty.",
    },
    {
        "question_id": "RAG-V1-009",
        "company": "Masan",
        "year": "2025",
        "question": "Masan đề cập những ưu tiên chiến lược nào cho năm 2025?",
        "expected_answer": "Masan tập trung vào tăng trưởng tiêu dùng, tối ưu vận hành, mở rộng hệ sinh thái, cải thiện hiệu quả tài chính và phục vụ khách hàng.",
    },
    {
        "question_id": "RAG-V1-010",
        "company": "FPT",
        "year": "2024",
        "question": "FPT báo cáo kết quả kinh doanh mảng công nghệ năm 2024 như thế nào?",
        "expected_answer": "FPT trình bày kết quả kinh doanh mảng công nghệ qua tăng trưởng doanh thu, lợi nhuận, hợp đồng, dịch vụ công nghệ và thị trường nước ngoài.",
    },
    {
        "question_id": "RAG-V1-011",
        "company": "Vinamilk",
        "year": "2023",
        "question": "Vinamilk trình bày các hoạt động phát triển bền vững trong năm 2023 như thế nào?",
        "expected_answer": "Vinamilk đề cập hoạt động môi trường, xã hội, quản trị, sản xuất bền vững, dinh dưỡng và trách nhiệm với cộng đồng.",
    },
    {
        "question_id": "RAG-V1-012",
        "company": "Masan",
        "year": "2024",
        "question": "Masan mô tả hoạt động bán lẻ và tiêu dùng trong báo cáo 2024 ra sao?",
        "expected_answer": "Masan mô tả hoạt động bán lẻ và tiêu dùng thông qua mạng lưới cửa hàng, hàng tiêu dùng, nền tảng phục vụ người tiêu dùng và tăng trưởng vận hành.",
    },
    {
        "question_id": "RAG-V1-013",
        "company": "FPT",
        "year": "2025",
        "question": "Báo cáo FPT 2025 đề cập định hướng phát triển nguồn nhân lực như thế nào?",
        "expected_answer": "FPT nhấn mạnh phát triển nhân lực công nghệ, đào tạo, thu hút nhân tài, nâng cao năng lực chuyên môn và gắn kết nhân viên.",
    },
    {
        "question_id": "RAG-V1-014",
        "company": "Vinamilk",
        "year": "2024",
        "question": "Vinamilk có những điểm nổi bật nào về quản trị doanh nghiệp trong năm 2024?",
        "expected_answer": "Vinamilk trình bày quản trị doanh nghiệp qua hội đồng quản trị, kiểm soát nội bộ, quản lý rủi ro, minh bạch thông tin và tuân thủ.",
    },
    {
        "question_id": "RAG-V1-015",
        "company": "Masan",
        "year": "2023",
        "question": "Masan báo cáo kết quả tài chính năm 2023 theo những nội dung chính nào?",
        "expected_answer": "Masan trình bày doanh thu, lợi nhuận, cơ cấu tài chính, hiệu quả vận hành và kết quả theo từng mảng kinh doanh.",
    },
    {
        "question_id": "RAG-V1-016",
        "company": "FPT",
        "year": "2023",
        "question": "FPT trình bày hoạt động thị trường nước ngoài trong năm 2023 như thế nào?",
        "expected_answer": "FPT đề cập tăng trưởng thị trường nước ngoài, dịch vụ công nghệ toàn cầu, khách hàng quốc tế và mở rộng hiện diện tại các khu vực trọng điểm.",
    },
    {
        "question_id": "RAG-V1-017",
        "company": "Vinamilk",
        "year": "2025",
        "question": "Vinamilk đề cập định hướng phát triển sản phẩm trong năm 2025 như thế nào?",
        "expected_answer": "Vinamilk tập trung đổi mới sản phẩm, nâng cao chất lượng, đáp ứng nhu cầu dinh dưỡng và phát triển danh mục sản phẩm phù hợp thị trường.",
    },
    {
        "question_id": "RAG-V1-018",
        "company": "Masan",
        "year": "2025",
        "question": "Masan mô tả việc tối ưu vận hành trong báo cáo 2025 ra sao?",
        "expected_answer": "Masan đề cập tối ưu vận hành, nâng cao hiệu quả chi phí, cải thiện chuỗi cung ứng, tăng năng suất và tích hợp các nền tảng kinh doanh.",
    },
    {
        "question_id": "RAG-V1-019",
        "company": "FPT",
        "year": "2024",
        "question": "FPT đề cập đến AI hoặc công nghệ mới trong báo cáo 2024 như thế nào?",
        "expected_answer": "FPT nhấn mạnh AI và công nghệ mới như động lực đổi mới, hỗ trợ chuyển đổi số, phát triển sản phẩm dịch vụ và nâng cao năng lực cạnh tranh.",
    },
    {
        "question_id": "RAG-V1-020",
        "company": "Vinamilk",
        "year": "2023",
        "question": "Vinamilk mô tả thị trường nội địa trong báo cáo thường niên 2023 như thế nào?",
        "expected_answer": "Vinamilk trình bày thị trường nội địa qua hoạt động bán hàng, kênh phân phối, nhu cầu tiêu dùng, thương hiệu và hiệu quả kinh doanh trong nước.",
    },
]


def cosine_similarity(model: SentenceTransformer, left: str, right: str) -> float:
    left_embedding = model.encode(left, normalize_embeddings=True)
    right_embedding = model.encode(right, normalize_embeddings=True)
    return float(util.cos_sim(left_embedding, right_embedding).item())


def format_sources(chunks: List[Dict[str, Any]]) -> str:
    sources = []
    seen = set()
    for chunk in chunks:
        source = Path(chunk.get("source", "unknown")).name
        page = chunk.get("page", -1)
        citation = f"[{source} - Page {page}]"
        if citation not in seen:
            seen.add(citation)
            sources.append(citation)
    return "; ".join(sources)


def compute_context_precision(
    model: SentenceTransformer,
    question: str,
    chunks: List[Dict[str, Any]],
    threshold: float,
) -> float:
    if not chunks:
        return 0.0

    question_embedding = model.encode(question, normalize_embeddings=True)
    chunk_embeddings = model.encode(
        [chunk.get("text", "") for chunk in chunks],
        normalize_embeddings=True,
    )
    scores = util.cos_sim(question_embedding, chunk_embeddings)[0]
    relevant_count = sum(1 for score in scores if float(score) >= threshold)
    return relevant_count / len(chunks)


def compute_context_recall(
    model: SentenceTransformer,
    expected_answer: str,
    chunks: List[Dict[str, Any]],
) -> float:
    if not chunks:
        return 0.0

    context = "\n".join(chunk.get("text", "") for chunk in chunks)
    return cosine_similarity(model, expected_answer, context)


def safe_generate_answer(pipeline: RAGPipelineV1, question: str) -> str:
    if not GENERATE_RAG_ANSWERS:
        return ""

    try:
        return pipeline.query(question)["answer"]
    except Exception as exc:
        return f"GENERATION_ERROR: {exc}"


def evaluate_rag(pipeline: RAGPipelineV1, eval_model: SentenceTransformer) -> Dict[str, Any]:
    rows = []
    manual_rows = []
    latencies_ms = []

    for i, item in enumerate(TEST_QUERIES, 1):
        question = item["question"]
        start = time.perf_counter()
        chunks = pipeline.retrieve(question, top_k=5)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(latency_ms)

        rag_answer = safe_generate_answer(pipeline, question)

        manual_rows.append(
            {
                "question_id": item["question_id"],
                "question": question,
                "rag_answer": rag_answer,
                "annotator1_score": "",
                "annotator2_score": "",
                "notes": "",
            }
        )

        if i <= EVAL_CONTEXT_LIMIT:
            rows.append(
                {
                    "question_id": item["question_id"],
                    "question": question,
                    "context_precision": compute_context_precision(
                        eval_model,
                        question,
                        chunks,
                        CONTEXT_PRECISION_THRESHOLD,
                    ),
                    "context_recall": compute_context_recall(
                        eval_model,
                        item["expected_answer"],
                        chunks,
                    ),
                    "retrieved_sources": format_sources(chunks),
                    "latency_ms": latency_ms,
                }
            )

        print(f"Evaluated {i}/{len(TEST_QUERIES)}: {item['question_id']}", flush=True)

    return {
        "rows": rows,
        "manual_rows": manual_rows,
        "latencies_ms": latencies_ms,
    }


def build_markdown_report(results: Dict[str, Any]) -> str:
    rows = results["rows"]
    avg_precision = sum(row["context_precision"] for row in rows) / len(rows)
    avg_recall = sum(row["context_recall"] for row in rows) / len(rows)
    avg_latency = sum(results["latencies_ms"]) / len(results["latencies_ms"])

    lines = [
        "# RAG V1 Baseline Evaluation",
        "",
        "## Setup",
        "",
        f"- **Pipeline:** `src/rag/rag_v1.py`",
        f"- **Retrieval:** ChromaDB cosine similarity, top_k=5",
        f"- **Evaluation model:** `{EVALUATION_MODEL}`",
        f"- **Context precision threshold:** `{CONTEXT_PRECISION_THRESHOLD}`",
        f"- **Questions:** 20 total; first {EVAL_CONTEXT_LIMIT} used for automatic Context Precision/Recall",
        "- **LLM judge:** Not used",
        "- **Manual scoring:** 1-5 scale with two annotators",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Average Context Precision | {avg_precision:.3f} |",
        f"| Average Context Recall | {avg_recall:.3f} |",
        f"| Average Retrieval Latency | {avg_latency:.2f} ms |",
        "",
        "## Automatic Evaluation Results",
        "",
        "| question_id | question | context_precision | context_recall | retrieved_sources |",
        "|---|---|---:|---:|---|",
    ]

    for row in rows:
        question = row["question"].replace("|", "\\|")
        sources = row["retrieved_sources"].replace("|", "\\|")
        lines.append(
            f"| {row['question_id']} | {question} | "
            f"{row['context_precision']:.3f} | {row['context_recall']:.3f} | {sources} |"
        )

    lines.extend(
        [
            "",
            "## Manual Scoring Protocol",
            "",
            "Manual scores should be filled in `docs/evaluation/manual_eval_template.csv` independently by two annotators.",
            "",
            "| Score | Meaning |",
            "|---:|---|",
            "| 1 | Completely wrong or unsupported |",
            "| 2 | Mostly wrong, minimal useful evidence |",
            "| 3 | Partially correct, incomplete or weakly sourced |",
            "| 4 | Mostly correct and reasonably sourced |",
            "| 5 | Fully correct, concise, and well-sourced |",
            "",
            "## Notes",
            "",
            "- Context Precision and Recall are embedding-similarity proxies, not human relevance judgments.",
            "- The evaluation model is aligned with the current multilingual RAG index for bilingual retrieval consistency.",
            "- To populate `rag_answer` with local Ollama outputs, run:",
            "",
            "```powershell",
            "$env:EVAL_RAG_GENERATE_ANSWERS='1'; .venv\\Scripts\\python.exe src\\evaluation\\eval_rag_v1.py",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def write_manual_template(rows: List[Dict[str, str]]) -> None:
    MANUAL_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANUAL_TEMPLATE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question_id",
                "question",
                "rag_answer",
                "annotator1_score",
                "annotator2_score",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    print("Loading RAG V1 pipeline...", flush=True)
    pipeline = RAGPipelineV1()
    pipeline.load_chunks(verbose=False)

    print(f"Loading evaluation embedding model: {EVALUATION_MODEL}", flush=True)
    eval_model = SentenceTransformer(
        EVALUATION_MODEL,
        cache_folder=str(EMBEDDING_CACHE_DIR),
    )

    print("Running offline RAG V1 evaluation...", flush=True)
    results = evaluate_rag(pipeline, eval_model)

    OUTPUT_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MARKDOWN.write_text(build_markdown_report(results), encoding="utf-8")
    write_manual_template(results["manual_rows"])

    print(f"Wrote report: {OUTPUT_MARKDOWN}", flush=True)
    print(f"Wrote manual template: {MANUAL_TEMPLATE}", flush=True)


if __name__ == "__main__":
    main()
