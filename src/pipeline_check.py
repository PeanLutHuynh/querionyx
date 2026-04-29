"""End-to-end V1 pipeline check for Querionyx.

Flow:
question -> RuleBasedRouter.classify() -> if RAG: RAGPipelineV1.query()

SQL and HYBRID branches are intentionally graceful placeholders because
Text-to-SQL and hybrid orchestration are Week 4 work.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.rag_v1 import RAGPipelineV1
from src.router.rule_based_router import RuleBasedRouter


TEST_CASES = [
    {
        "question": "FPT có những mảng kinh doanh chính nào?",
        "expected_route": "RAG",
    },
    {
        "question": "Có bao nhiêu sản phẩm trong hệ thống?",
        "expected_route": "SQL",
    },
    {
        "question": "Chiến lược của Vinamilk là gì và tổng đơn hàng là bao nhiêu?",
        "expected_route": "HYBRID",
    },
]


def normalize_expected_route(expected_route: str) -> str:
    return expected_route.split()[0].strip().upper()


def ensure_rag_pipeline(pipeline: Optional[RAGPipelineV1]) -> RAGPipelineV1:
    if pipeline is not None:
        return pipeline

    rag_pipeline = RAGPipelineV1(llm_timeout_seconds=30)
    rag_pipeline.load_chunks(verbose=False)
    return rag_pipeline


def run_rag_branch(pipeline: RAGPipelineV1, question: str) -> Dict[str, Any]:
    start = time.perf_counter()
    result = pipeline.query(question, top_k=5)
    latency_ms = (time.perf_counter() - start) * 1000

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "latency_ms": latency_ms,
    }


def print_rag_result(result: Dict[str, Any]) -> None:
    print(f"  RAG latency: {result['latency_ms']:.2f} ms")
    print(f"  Answer: {result['answer']}")
    if "timed out" in result["answer"].lower() or "unable to connect" in result["answer"].lower():
        print("  RAG status: graceful LLM fallback; retrieval sources are still available.")
    print(f"  Sources ({len(result['sources'])}):")
    for source in result["sources"]:
        print(f"    - {source}")


def run_rag_retrieval_preview(pipeline: RAGPipelineV1, question: str) -> Dict[str, Any]:
    start = time.perf_counter()
    chunks = pipeline.retrieve(question, top_k=5)
    latency_ms = (time.perf_counter() - start) * 1000

    selected_chunks = pipeline._select_generation_chunks(chunks)
    return {
        "sources": pipeline._format_citations(selected_chunks),
        "latency_ms": latency_ms,
        "context_chunks": chunks,
    }


def print_retrieval_preview(result: Dict[str, Any]) -> None:
    print(f"  RAG retrieval latency: {result['latency_ms']:.2f} ms")
    print(f"  Retrieved context chunks: {len(result['context_chunks'])}")
    print(f"  Preview sources ({len(result['sources'])}):")
    for source in result["sources"]:
        print(f"    - {source}")


def main() -> None:
    print("=" * 80)
    print("Querionyx V1 End-to-End Pipeline Check")
    print("=" * 80)

    router = RuleBasedRouter()
    rag_pipeline: Optional[RAGPipelineV1] = None
    passed = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        question = test_case["question"]
        expected_route = normalize_expected_route(test_case["expected_route"])

        print(f"\nTest {i}: {question}")
        route = router.classify(question)
        route_passed = route.intent == expected_route
        print(f"  Expected route: {expected_route}")
        print(f"  Predicted route: {route.intent}")
        print(f"  Router reasoning: {route.reasoning}")
        print(f"  Route check: {'PASS' if route_passed else 'FAIL'}")

        if route.intent == "RAG":
            try:
                rag_pipeline = ensure_rag_pipeline(rag_pipeline)
                result = run_rag_branch(rag_pipeline, question)
                print_rag_result(result)
            except Exception as exc:
                route_passed = False
                print(f"  RAG branch failed gracefully: {exc}")

        elif route.intent == "SQL":
            # TODO(Week 4): plug in Text-to-SQL execution branch here.
            print("  SQL branch not implemented in V1. Graceful placeholder returned.")

        elif route.intent == "HYBRID":
            # TODO(Week 4): orchestrate RAG + Text-to-SQL and merge evidence here.
            print("  HYBRID branch not implemented in V1. Running partial RAG retrieval-only preview.")
            try:
                rag_pipeline = ensure_rag_pipeline(rag_pipeline)
                result = run_rag_retrieval_preview(rag_pipeline, question)
                print_retrieval_preview(result)
                print("  HYBRID status: PARTIAL PASS (RAG retrieval only; SQL branch pending)")
            except Exception as exc:
                route_passed = False
                print(f"  HYBRID partial branch failed gracefully: {exc}")

        else:
            route_passed = False
            print(f"  Unknown route '{route.intent}'.")

        if route_passed:
            passed += 1

        print(f"  Test result: {'PASS' if route_passed else 'FAIL'}")

    print("\n" + "=" * 80)
    print(f"Pipeline check complete: {passed}/{len(TEST_CASES)} route checks passed")
    if passed == len(TEST_CASES):
        print("V1 pipeline stable: router works, RAG retrieval loads, SQL/HYBRID fail gracefully.")
    else:
        print("V1 pipeline check found route or branch issues. See details above.")
    print("=" * 80)


if __name__ == "__main__":
    main()
