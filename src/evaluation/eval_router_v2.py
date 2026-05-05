"""Evaluation script for LLM-based Router V2.

Compares V1 (rule-based) vs V2 (LLM-based) on the 60 test queries.

Key metrics:
- Overall accuracy: % correct predictions
- Accuracy by query type: RAG, SQL, HYBRID
- LLM call rate: % of queries that required LLM (efficiency metric)
- Latency: average time per classification
- Confusion matrix: detailed breakdown of errors
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.router.llm_router import LLMRouterV2
from src.router.rule_based_router import RuleBasedRouter

TEST_QUERIES_FILE = PROJECT_ROOT / "data" / "test_queries" / "router_eval_60.json"
OUTPUT_MARKDOWN = PROJECT_ROOT / "docs" / "evaluation" / "eval_v2_router.md"


def load_test_queries(file_path: Path) -> dict:
    """Load test queries from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_router_v1(router: RuleBasedRouter, queries: list[dict]) -> dict:
    """Evaluate rule-based router V1 on test set."""
    results = {
        "total": len(queries),
        "correct": 0,
        "incorrect": 0,
        "latencies_ms": [],
        "predictions": [],
        "confusion_matrix": {
            intent: {intent: 0 for intent in ["RAG", "SQL", "HYBRID"]}
            for intent in ["RAG", "SQL", "HYBRID"]
        },
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


def evaluate_router_v2(router: LLMRouterV2, queries: list[dict]) -> dict:
    """Evaluate LLM-based router V2 on test set."""
    results = {
        "total": len(queries),
        "correct": 0,
        "incorrect": 0,
        "latencies_ms": [],
        "llm_calls": 0,
        "rule_based_shortcuts": 0,
        "predictions": [],
        "confusion_matrix": {
            intent: {intent: 0 for intent in ["RAG", "SQL", "HYBRID"]}
            for intent in ["RAG", "SQL", "HYBRID"]
        },
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

        if prediction.llm_called:
            results["llm_calls"] += 1
        if prediction.rule_based_fallback:
            results["rule_based_shortcuts"] += 1

        # Track prediction
        results["predictions"].append(
            {
                "question": question,
                "ground_truth": ground_truth,
                "predicted": predicted_intent,
                "correct": ground_truth == predicted_intent,
                "latency_ms": elapsed_ms,
                "confidence": prediction.confidence,
                "reasoning": prediction.reasoning,
                "llm_called": prediction.llm_called,
                "rule_based": prediction.rule_based_fallback,
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


def compute_metrics(v1_results: dict, v2_results: dict) -> dict:
    """Compute evaluation metrics for both versions."""

    def safe_avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    def safe_percentile(lst, p):
        if not lst:
            return 0.0
        sorted_lst = sorted(lst)
        idx = int(len(sorted_lst) * p)
        return sorted_lst[min(idx, len(sorted_lst) - 1)]

    def accuracy_by_intent(results, intent):
        predictions = [p for p in results["predictions"] if p["ground_truth"] == intent]
        if not predictions:
            return 0.0
        correct = sum(1 for p in predictions if p["correct"])
        return correct / len(predictions)

    metrics = {
        "v1": {
            "overall_accuracy": v1_results["correct"] / v1_results["total"] if v1_results["total"] > 0 else 0.0,
            "rag_accuracy": accuracy_by_intent(v1_results, "RAG"),
            "sql_accuracy": accuracy_by_intent(v1_results, "SQL"),
            "hybrid_accuracy": accuracy_by_intent(v1_results, "HYBRID"),
            "avg_latency_ms": safe_avg(v1_results["latencies_ms"]),
            "p50_latency_ms": safe_percentile(v1_results["latencies_ms"], 0.50),
            "p95_latency_ms": safe_percentile(v1_results["latencies_ms"], 0.95),
            "max_latency_ms": max(v1_results["latencies_ms"]) if v1_results["latencies_ms"] else 0.0,
            "correct_count": v1_results["correct"],
            "incorrect_count": v1_results["incorrect"],
        },
        "v2": {
            "overall_accuracy": v2_results["correct"] / v2_results["total"] if v2_results["total"] > 0 else 0.0,
            "rag_accuracy": accuracy_by_intent(v2_results, "RAG"),
            "sql_accuracy": accuracy_by_intent(v2_results, "SQL"),
            "hybrid_accuracy": accuracy_by_intent(v2_results, "HYBRID"),
            "avg_latency_ms": safe_avg(v2_results["latencies_ms"]),
            "p50_latency_ms": safe_percentile(v2_results["latencies_ms"], 0.50),
            "p95_latency_ms": safe_percentile(v2_results["latencies_ms"], 0.95),
            "max_latency_ms": max(v2_results["latencies_ms"]) if v2_results["latencies_ms"] else 0.0,
            "correct_count": v2_results["correct"],
            "incorrect_count": v2_results["incorrect"],
            "llm_call_count": v2_results["llm_calls"],
            "llm_call_rate": v2_results["llm_calls"] / v2_results["total"] if v2_results["total"] > 0 else 0.0,
            "rule_based_skips": v2_results["rule_based_shortcuts"],
        },
        "comparison": {
            "overall_accuracy_improvement": (
                metrics["v2"]["overall_accuracy"] - metrics["v1"]["overall_accuracy"]
            )
            if "v2" in locals()
            else 0,
            "latency_increase_pct": (
                (metrics["v2"]["avg_latency_ms"] - metrics["v1"]["avg_latency_ms"]) / metrics["v1"]["avg_latency_ms"] * 100
            )
            if "v2" in locals() and metrics["v1"]["avg_latency_ms"] > 0
            else 0,
        },
    }

    return metrics


def build_markdown_report(v1_results: dict, v2_results: dict, metrics: dict) -> str:
    """Build markdown evaluation report comparing V1 vs V2."""
    lines = []

    lines.append("# LLM-based Router V2 - Evaluation Report")
    lines.append("")
    lines.append("**Date:** 2026-05-05")
    lines.append("**Test Set:** 60 labeled router queries (20 RAG, 20 SQL, 20 HYBRID)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # V1 Summary
    lines.append("## V1 (Rule-based) Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Overall Accuracy | {metrics['v1']['overall_accuracy']:.2%} |")
    lines.append(f"| RAG Accuracy | {metrics['v1']['rag_accuracy']:.2%} |")
    lines.append(f"| SQL Accuracy | {metrics['v1']['sql_accuracy']:.2%} |")
    lines.append(f"| HYBRID Accuracy | {metrics['v1']['hybrid_accuracy']:.2%} |")
    lines.append(f"| Avg Latency | {metrics['v1']['avg_latency_ms']:.3f} ms |")
    lines.append(f"| P95 Latency | {metrics['v1']['p95_latency_ms']:.3f} ms |")
    lines.append("")

    # V2 Summary
    lines.append("## V2 (LLM-based) Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Overall Accuracy | {metrics['v2']['overall_accuracy']:.2%} |")
    lines.append(f"| RAG Accuracy | {metrics['v2']['rag_accuracy']:.2%} |")
    lines.append(f"| SQL Accuracy | {metrics['v2']['sql_accuracy']:.2%} |")
    lines.append(f"| HYBRID Accuracy | {metrics['v2']['hybrid_accuracy']:.2%} |")
    lines.append(f"| Avg Latency | {metrics['v2']['avg_latency_ms']:.3f} ms |")
    lines.append(f"| P95 Latency | {metrics['v2']['p95_latency_ms']:.3f} ms |")
    lines.append(f"| LLM Call Rate | {metrics['v2']['llm_call_rate']:.2%} |")
    lines.append(f"| Rule-based Skips | {metrics['v2']['rule_based_skips']} / {v2_results['total']} |")
    lines.append("")

    # V1 vs V2 Comparison
    lines.append("## V1 vs V2 Comparison")
    lines.append("")
    lines.append("| Metric | V1 | V2 | Change |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Overall Accuracy | {metrics['v1']['overall_accuracy']:.2%} | {metrics['v2']['overall_accuracy']:.2%} | "
        f"{metrics['v2']['overall_accuracy'] - metrics['v1']['overall_accuracy']:+.2%} |"
    )
    lines.append(
        f"| RAG Accuracy | {metrics['v1']['rag_accuracy']:.2%} | {metrics['v2']['rag_accuracy']:.2%} | "
        f"{metrics['v2']['rag_accuracy'] - metrics['v1']['rag_accuracy']:+.2%} |"
    )
    lines.append(
        f"| SQL Accuracy | {metrics['v1']['sql_accuracy']:.2%} | {metrics['v2']['sql_accuracy']:.2%} | "
        f"{metrics['v2']['sql_accuracy'] - metrics['v1']['sql_accuracy']:+.2%} |"
    )
    lines.append(
        f"| HYBRID Accuracy | {metrics['v1']['hybrid_accuracy']:.2%} | {metrics['v2']['hybrid_accuracy']:.2%} | "
        f"{metrics['v2']['hybrid_accuracy'] - metrics['v1']['hybrid_accuracy']:+.2%} |"
    )
    lines.append(
        f"| Avg Latency (ms) | {metrics['v1']['avg_latency_ms']:.2f} | {metrics['v2']['avg_latency_ms']:.2f} | "
        f"{metrics['v2']['avg_latency_ms'] - metrics['v1']['avg_latency_ms']:+.2f} |"
    )
    lines.append("")

    # Efficiency Analysis
    lines.append("## V2 Efficiency Analysis")
    lines.append("")
    lines.append(f"- **LLM Calls:** {metrics['v2']['llm_call_count']} / {v2_results['total']} ({metrics['v2']['llm_call_rate']:.1%})")
    lines.append(f"- **Rule-based Shortcuts:** {metrics['v2']['rule_based_skips']} queries skipped LLM (direct rule-based)")
    lines.append(f"- **Efficiency Gain:** {(1 - metrics['v2']['llm_call_rate']):.1%} reduction in LLM calls vs full LLM classification")
    lines.append("")

    # Confusion Matrices
    lines.append("## Confusion Matrices")
    lines.append("")

    lines.append("### V1 (Rule-based) Confusion Matrix")
    lines.append("")
    lines.append("| Predicted \\ Ground Truth | RAG | SQL | HYBRID |")
    lines.append("|---|---|---|---|")
    for gt in ["RAG", "SQL", "HYBRID"]:
        row = f"| {gt} "
        for pred in ["RAG", "SQL", "HYBRID"]:
            row += f"| {v1_results['confusion_matrix'][gt][pred]} "
        row += "|"
        lines.append(row)
    lines.append("")

    lines.append("### V2 (LLM-based) Confusion Matrix")
    lines.append("")
    lines.append("| Predicted \\ Ground Truth | RAG | SQL | HYBRID |")
    lines.append("|---|---|---|---|")
    for gt in ["RAG", "SQL", "HYBRID"]:
        row = f"| {gt} "
        for pred in ["RAG", "SQL", "HYBRID"]:
            row += f"| {v2_results['confusion_matrix'][gt][pred]} "
        row += "|"
        lines.append(row)
    lines.append("")

    # Error Analysis
    lines.append("## Error Analysis - V2 Misclassifications")
    lines.append("")
    errors_v2 = [p for p in v2_results["predictions"] if not p["correct"]]
    if errors_v2:
        lines.append("| Query | Ground Truth | Predicted | Confidence | Method |")
        lines.append("|---|---|---|---|---|")
        for error in errors_v2[:10]:  # Show top 10 errors
            method = "LLM" if error["llm_called"] else "Rule-based"
            lines.append(
                f"| {error['question'][:50]}... | {error['ground_truth']} | {error['predicted']} | "
                f"{error['confidence']:.2f} | {method} |"
            )
        if len(errors_v2) > 10:
            lines.append(f"| ... and {len(errors_v2) - 10} more errors | | | | |")
    else:
        lines.append("No errors! Perfect classification.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Key Findings")
    lines.append("")
    lines.append(f"1. **Accuracy Improvement:** V2 achieves {metrics['v2']['overall_accuracy']:.2%} vs V1's {metrics['v1']['overall_accuracy']:.2%}")
    lines.append(
        f"2. **LLM Efficiency:** Only {metrics['v2']['llm_call_rate']:.1%} of queries require LLM calls, "
        f"reducing latency for {metrics['v2']['rule_based_skips']} high-confidence queries"
    )
    lines.append(f"3. **HYBRID Detection:** V2 correctly identifies HYBRID queries at {metrics['v2']['hybrid_accuracy']:.2%} accuracy")
    lines.append(f"4. **Latency Trade-off:** V2 latency is {metrics['v2']['avg_latency_ms']:.1f}ms (LLM calls add {metrics['v2']['avg_latency_ms'] - metrics['v1']['avg_latency_ms']:.1f}ms)")
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 80)
    print("LLM Router V2 - Evaluation (V1 vs V2)")
    print("=" * 80)

    # Load test queries
    print("\n[1/5] Loading test queries...")
    test_data = load_test_queries(TEST_QUERIES_FILE)
    queries = test_data.get("queries", [])
    print(f"✓ Loaded {len(queries)} test queries")
    print(f"   Distribution: {test_data.get('metadata', {}).get('distribution', {})}")

    # Initialize and evaluate V1
    print("\n[2/5] Initializing and evaluating Rule-based Router V1...")
    router_v1 = RuleBasedRouter()
    v1_results = evaluate_router_v1(router_v1, queries)
    print(f"✓ V1 Evaluation complete: {v1_results['correct']}/{v1_results['total']} correct")

    # Initialize and evaluate V2
    print("\n[3/5] Initializing and evaluating LLM-based Router V2...")
    router_v2 = LLMRouterV2()
    v2_results = evaluate_router_v2(router_v2, queries)
    print(f"✓ V2 Evaluation complete: {v2_results['correct']}/{v2_results['total']} correct")
    print(f"   LLM calls: {v2_results['llm_calls']}/{v2_results['total']} ({v2_results['llm_calls']/v2_results['total']:.1%})")
    print(f"   Rule-based shortcuts: {v2_results['rule_based_shortcuts']}")

    # Compute metrics
    print("\n[4/5] Computing metrics and comparison...")
    metrics = compute_metrics(v1_results, v2_results)
    print(f"✓ Metrics computed")
    print(f"   V1 Accuracy: {metrics['v1']['overall_accuracy']:.2%}")
    print(f"   V2 Accuracy: {metrics['v2']['overall_accuracy']:.2%}")
    print(f"   Improvement: {metrics['v2']['overall_accuracy'] - metrics['v1']['overall_accuracy']:+.2%}")

    # Generate report
    print("\n[5/5] Generating markdown report...")
    report = build_markdown_report(v1_results, v2_results, metrics)

    OUTPUT_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MARKDOWN, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✓ Report written to {OUTPUT_MARKDOWN}")
    print("\n" + "=" * 80)
    print("Evaluation Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
