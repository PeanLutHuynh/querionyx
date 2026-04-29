"""Evaluation script for Rule-based Router V1 baseline."""

import json
import sys
import time
from pathlib import Path
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.router.rule_based_router import RuleBasedRouter

TEST_QUERIES_FILE = PROJECT_ROOT / "data" / "test_queries" / "router_eval_60.json"
OUTPUT_MARKDOWN = PROJECT_ROOT / "docs" / "eval_v1_router_baseline.md"


def load_test_queries(file_path: Path) -> dict:
    """Load test queries from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_router(router: RuleBasedRouter, queries: list[dict]) -> dict:
    """
    Evaluate router on test set.

    Args:
        router: RuleBasedRouter instance
        queries: List of query dicts with question and ground_truth_intent

    Returns:
        Dictionary with evaluation metrics
    """
    results = {
        "total": len(queries),
        "correct": 0,
        "incorrect": 0,
        "latencies_ms": [],
        "predictions": [],
        "confusion_matrix": {intent: {intent: 0 for intent in ["RAG", "SQL", "HYBRID"]} for intent in ["RAG", "SQL", "HYBRID"]},
    }

    for query in queries:
        question = query["question"]
        ground_truth = query["ground_truth_intent"]

        # Measure latency
        start = time.perf_counter()
        prediction = router.classify(question)
        elapsed_ms = (time.perf_counter() - start) * 1000

        predicted_intent = prediction.intent
        results["latencies_ms"].append(elapsed_ms)

        # Track prediction
        results["predictions"].append(
            {
                "question": question,
                "ground_truth": ground_truth,
                "predicted": predicted_intent,
                "correct": ground_truth == predicted_intent,
                "latency_ms": elapsed_ms,
                "reasoning": prediction.reasoning,
            }
        )

        # Update confusion matrix
        results["confusion_matrix"][ground_truth][predicted_intent] += 1

        # Count correct/incorrect
        if ground_truth == predicted_intent:
            results["correct"] += 1
        else:
            results["incorrect"] += 1

    return results


def compute_metrics(results: dict) -> dict:
    """Compute evaluation metrics from results."""
    queries = results["predictions"]
    total = results["total"]

    # Split by intent group
    unstructured = [q for q in queries if q["ground_truth"] == "RAG"]
    structured = [q for q in queries if q["ground_truth"] == "SQL"]
    hybrid = [q for q in queries if q["ground_truth"] == "HYBRID"]

    metrics = {
        "overall_accuracy": results["correct"] / total if total > 0 else 0.0,
        "unstructured_accuracy": sum(1 for q in unstructured if q["correct"]) / len(unstructured) if unstructured else 0.0,
        "structured_accuracy": sum(1 for q in structured if q["correct"]) / len(structured) if structured else 0.0,
        "hybrid_accuracy": sum(1 for q in hybrid if q["correct"]) / len(hybrid) if hybrid else 0.0,
        "avg_latency_ms": sum(results["latencies_ms"]) / len(results["latencies_ms"]) if results["latencies_ms"] else 0.0,
        "min_latency_ms": min(results["latencies_ms"]) if results["latencies_ms"] else 0.0,
        "max_latency_ms": max(results["latencies_ms"]) if results["latencies_ms"] else 0.0,
        "p50_latency_ms": sorted(results["latencies_ms"])[len(results["latencies_ms"]) // 2] if results["latencies_ms"] else 0.0,
        "p95_latency_ms": sorted(results["latencies_ms"])[int(len(results["latencies_ms"]) * 0.95)] if results["latencies_ms"] else 0.0,
        "correct_count": results["correct"],
        "incorrect_count": results["incorrect"],
    }

    return metrics


def build_markdown_report(results: dict, metrics: dict) -> str:
    """Build markdown evaluation report."""
    lines = []

    lines.append("# Rule-based Router V1 - Baseline Evaluation Report")
    lines.append("")
    lines.append("**Date:** 2026-05-01")
    lines.append("")
    lines.append("**Purpose:** Establish baseline for Router accuracy comparison (V1 vs V2 LLM-based vs V3 Adaptive).")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary metrics
    lines.append("## Summary Metrics")
    lines.append("")
    lines.append(f"- **Total Queries:** {results['total']}")
    lines.append(f"- **Correct Predictions:** {metrics['correct_count']}")
    lines.append(f"- **Incorrect Predictions:** {metrics['incorrect_count']}")
    lines.append(f"- **Overall Accuracy:** {metrics['overall_accuracy']:.2%}")
    lines.append("")

    # Accuracy by group
    lines.append("## Accuracy by Query Type")
    lines.append("")
    lines.append("| Query Type | Count | Accuracy | Notes |")
    lines.append("|---|---|---|---|")
    lines.append(f"| UNSTRUCTURED (RAG) | 20 | {metrics['unstructured_accuracy']:.2%} | Document-based questions |")
    lines.append(f"| STRUCTURED (SQL) | 20 | {metrics['structured_accuracy']:.2%} | Database queries |")
    lines.append(f"| HYBRID | 20 | {metrics['hybrid_accuracy']:.2%} | Require both sources - **Expected ~0%** |")
    lines.append("")

    # Latency analysis
    lines.append("## Latency Analysis")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Average | {metrics['avg_latency_ms']:.3f} ms |")
    lines.append(f"| Min | {metrics['min_latency_ms']:.3f} ms |")
    lines.append(f"| Max | {metrics['max_latency_ms']:.3f} ms |")
    lines.append(f"| P50 | {metrics['p50_latency_ms']:.3f} ms |")
    lines.append(f"| P95 | {metrics['p95_latency_ms']:.3f} ms |")
    lines.append("")

    # Confusion matrix
    lines.append("## Confusion Matrix (3×3)")
    lines.append("")
    lines.append("|  | Predicted RAG | Predicted SQL | Predicted HYBRID |")
    lines.append("|---|---|---|---|")
    for ground_truth_intent in ["RAG", "SQL", "HYBRID"]:
        conf = results["confusion_matrix"][ground_truth_intent]
        lines.append(f"| Actual {ground_truth_intent} | {conf['RAG']} | {conf['SQL']} | {conf['HYBRID']} |")
    lines.append("")

    # Error analysis
    lines.append("## Error Analysis")
    lines.append("")
    incorrect_predictions = [p for p in results["predictions"] if not p["correct"]]
    if incorrect_predictions:
        lines.append(f"**Total Errors:** {len(incorrect_predictions)}")
        lines.append("")
        lines.append("### Incorrect Predictions (Sample)")
        lines.append("")
        for i, pred in enumerate(incorrect_predictions[:10], 1):  # Show first 10 errors
            lines.append(f"**Error {i}:**")
            lines.append(f"- Question: {pred['question']}")
            lines.append(f"- Expected: {pred['ground_truth']}")
            lines.append(f"- Predicted: {pred['predicted']}")
            lines.append(f"- Reasoning: {pred['reasoning']}")
            lines.append("")
    else:
        lines.append("✅ No errors found!")
        lines.append("")

    # Key findings
    lines.append("## Key Findings")
    lines.append("")
    lines.append("1. **HYBRID Accuracy Expected ~0%**")
    lines.append("   - Rule-based router cannot handle HYBRID queries that require both RAG and SQL sources.")
    lines.append("   - This establishes the baseline justification for implementing LLM-based Router (V2) in week 4.")
    lines.append("")
    lines.append("2. **UNSTRUCTURED and STRUCTURED handling**")
    lines.append("   - Rule-based keyword matching works well for clear intent signals.")
    lines.append(f"   - UNSTRUCTURED accuracy: {metrics['unstructured_accuracy']:.1%}")
    lines.append(f"   - STRUCTURED accuracy: {metrics['structured_accuracy']:.1%}")
    lines.append("")
    lines.append("3. **Performance**")
    lines.append(f"   - Very fast: avg {metrics['avg_latency_ms']:.2f}ms (deterministic, no LLM calls)")
    lines.append(f"   - Suitable for real-time deployment as lightweight baseline")
    lines.append("")

    # Conclusion
    lines.append("## Conclusion")
    lines.append("")
    lines.append("Rule-based Router V1 provides a deterministic, fast baseline for intent classification.")
    lines.append("It performs well for clear-signal queries (UNSTRUCTURED / STRUCTURED) but fails on ambiguous")
    lines.append("HYBRID queries. This data motivates the development of LLM-based and Adaptive routers in subsequent weeks.")
    lines.append("")

    return "\n".join(lines)


def main():
    """Run evaluation."""
    print("Loading router and test queries...")
    router = RuleBasedRouter()
    test_data = load_test_queries(TEST_QUERIES_FILE)
    queries = test_data["queries"]

    print(f"Evaluating on {len(queries)} queries...")
    results = evaluate_router(router, queries)

    print("Computing metrics...")
    metrics = compute_metrics(results)

    print("\n=== Evaluation Results ===")
    print(f"Overall Accuracy: {metrics['overall_accuracy']:.2%}")
    print(f"  - UNSTRUCTURED (RAG): {metrics['unstructured_accuracy']:.2%}")
    print(f"  - STRUCTURED (SQL): {metrics['structured_accuracy']:.2%}")
    print(f"  - HYBRID: {metrics['hybrid_accuracy']:.2%}")
    print(f"\nAverage Latency: {metrics['avg_latency_ms']:.3f} ms")
    print(f"P95 Latency: {metrics['p95_latency_ms']:.3f} ms")

    # Generate markdown report
    print(f"\nGenerating report to {OUTPUT_MARKDOWN}...")
    markdown_report = build_markdown_report(results, metrics)

    OUTPUT_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MARKDOWN, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    print(f"✅ Report saved to {OUTPUT_MARKDOWN}")

    # Also save detailed results as JSON for later reference
    results_json_path = PROJECT_ROOT / "docs" / "eval_v1_router_results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metrics": metrics,
                "confusion_matrix": results["confusion_matrix"],
                "total_predictions": len(results["predictions"]),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"✅ Detailed results saved to {results_json_path}")


if __name__ == "__main__":
    main()
