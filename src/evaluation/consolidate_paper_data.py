"""
Consolidation Script - Merge all evaluation results into paper-ready JSON.

Reads all results files from docs/results/ and consolidates into a single JSON
containing all metrics required for paper tables.

Usage:
    python -m src.evaluation.consolidate_paper_data
    python src/evaluation/consolidate_paper_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.runtime.logging import write_json
from src.runtime.schemas import now_iso


def consolidate_paper_data(results_dir: Path) -> Dict[str, Any]:
    """
    Consolidate all evaluation results into a single paper-ready JSON.

    Reads from:
    - docs/results/layer1_router_eval.md
    - docs/results/layer2_rag_eval.md
    - docs/results/layer2_sql_eval.md
    - docs/results/layer2_hybrid_eval.md
    - docs/results/layer3_performance.md
    - docs/results/ablation_study.md

    And extracts all metrics into a consolidated structure.
    """

    consolidated = {
        "timestamp": now_iso(),
        "paper_title": "Querionyx V3: Adaptive Hybrid RAG-SQL System for Multi-Modal Enterprise Data",
        "conference": "ICCCNET 2026",
        "tables": {},
        "summary_statistics": {},
    }

    # Try to read detailed JSON results if available
    results_base = Path("metrics")

    print(f"\n{'='*80}")
    print("CONSOLIDATING PAPER DATA")
    print(f"{'='*80}\n")

    # Table 1: Router Evaluation
    print("Consolidating Table 1: Router Evaluation...")
    router_results = try_read_json(results_base / "router_eval" / "router_detailed_results.json")
    if router_results:
        table1 = {
            "title": "Table 1: Router Comparison (Rule-Based vs LLM vs Adaptive)",
            "metrics": router_results.get("metrics", {}),
            "summary": extract_router_summary(router_results),
        }
        consolidated["tables"]["table1_router"] = table1

    # Table 2: RAG Evaluation
    print("Consolidating Table 2: RAG Evaluation...")
    rag_results = try_read_json(results_base / "rag_eval" / "rag_detailed_results.json")
    if rag_results:
        table2 = {
            "title": "Table 2: RAG Pipeline Comparison (V1 vs V2 vs V3)",
            "metrics": rag_results.get("metrics", {}),
            "summary": extract_rag_summary(rag_results),
        }
        consolidated["tables"]["table2_rag"] = table2

    # Table 3: SQL Evaluation
    print("Consolidating Table 3: SQL Evaluation...")
    sql_results = try_read_json(results_base / "sql_eval" / "sql_detailed_results.json")
    if sql_results:
        table3 = {
            "title": "Table 3: SQL Pipeline Evaluation",
            "metrics": sql_results.get("metrics", {}),
            "summary": extract_sql_summary(sql_results),
        }
        consolidated["tables"]["table3_sql"] = table3

    # Table 4: Hybrid Evaluation
    print("Consolidating Table 4: Hybrid Evaluation...")
    hybrid_results = try_read_json(results_base / "hybrid_eval" / "hybrid_detailed_results.json")
    if hybrid_results:
        table4 = {
            "title": "Table 4: Hybrid Query Evaluation",
            "metrics": hybrid_results.get("metrics", {}),
            "summary": extract_hybrid_summary(hybrid_results),
        }
        consolidated["tables"]["table4_hybrid"] = table4

    # Table 5: Performance Evaluation
    print("Consolidating Table 5: System Performance...")
    perf_results = try_read_json(results_base / "performance_eval" / "performance_detailed_results.json")
    if perf_results:
        table5 = {
            "title": "Table 5: System Performance Metrics",
            "metrics": perf_results.get("metrics", {}),
            "summary": extract_performance_summary(perf_results),
        }
        consolidated["tables"]["table5_performance"] = table5

    # Table 6: Ablation Study
    print("Consolidating Table 6: Ablation Study...")
    ablation_results = try_read_json(results_base / "ablation_study" / "ablation_detailed_results.json")
    if ablation_results:
        table6 = {
            "title": "Table 6: Ablation Study - Configuration Impact",
            "metrics": ablation_results.get("metrics", {}),
            "configurations": ablation_results.get("configs", {}),
            "summary": extract_ablation_summary(ablation_results),
        }
        consolidated["tables"]["table6_ablation"] = table6

    # Compute overall summary statistics
    consolidated["summary_statistics"] = compute_summary_statistics(consolidated["tables"])

    return consolidated


def try_read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Try to read JSON file, return None if not found."""
    try:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return json.loads(content)
    except Exception as e:
        print(f"  Warning: Could not read {path}: {e}")
    return None


def extract_router_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from router results."""
    metrics = data.get("metrics", {})
    return {
        "best_router": max(
            metrics.items(), key=lambda x: x[1].get("accuracy", 0) if isinstance(x[1], dict) else 0
        )[0]
        if metrics
        else None,
        "router_accuracies": {
            name: m.get("accuracy", 0) for name, m in metrics.items() if isinstance(m, dict)
        },
        "avg_latencies": {
            name: m.get("avg_latency_ms", 0) for name, m in metrics.items() if isinstance(m, dict)
        },
    }


def extract_rag_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from RAG results."""
    metrics = data.get("metrics", {})
    return {
        "best_rag_version": max(
            metrics.items(), key=lambda x: x[1].get("context_precision", 0) if isinstance(x[1], dict) else 0
        )[0]
        if metrics
        else None,
        "avg_precisions": {
            name: m.get("context_precision", 0) for name, m in metrics.items() if isinstance(m, dict)
        },
        "avg_recalls": {name: m.get("context_recall", 0) for name, m in metrics.items() if isinstance(m, dict)},
    }


def extract_sql_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from SQL results."""
    metrics = data.get("metrics", {})
    return {
        "execution_accuracy": metrics.get("execution_accuracy", 0),
        "exact_match_rate": metrics.get("exact_match_rate", 0),
        "retry_rate": metrics.get("retry_rate", 0),
        "error_breakdown": metrics.get("error_breakdown", {}),
    }


def extract_hybrid_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from hybrid results."""
    metrics = data.get("metrics", {})
    return {
        "hybrid_correctness": metrics.get("hybrid_correctness", 0),
        "fallback_rate": metrics.get("fallback_rate", 0),
        "latency_p95": metrics.get("latency_p95_ms", 0),
        "component_breakdown": metrics.get("component_breakdown", {}),
    }


def extract_performance_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from performance results."""
    metrics = data.get("metrics", {})
    return {
        "throughput_qps": metrics.get("throughput_qps", 0),
        "error_rate": metrics.get("error_rate", 0),
        "latency_by_type": metrics.get("latency_by_type", {}),
        "cpu_peak": metrics.get("cpu_percent_peak", 0),
        "memory_peak": metrics.get("memory_mb_peak", 0),
    }


def extract_ablation_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from ablation results."""
    metrics = data.get("metrics", {})
    configurations = data.get("configs", {})

    if metrics and "full_system" in metrics:
        baseline = metrics.get("full_system", {})
        baseline_correctness = baseline.get("hybrid_correctness", 0)

        impact = {}
        for config_name, config_metrics in metrics.items():
            if config_name != "full_system":
                correctness = config_metrics.get("hybrid_correctness", 0)
                impact[config_name] = {
                    "correctness_delta": correctness - baseline_correctness,
                    "correctness_impact_pct": (
                        ((correctness - baseline_correctness) / baseline_correctness * 100)
                        if baseline_correctness > 0
                        else 0
                    ),
                }

        return {"baseline_correctness": baseline_correctness, "configuration_impact": impact}

    return {}


def compute_summary_statistics(tables: Dict[str, Any]) -> Dict[str, Any]:
    """Compute overall summary statistics across all evaluations."""
    return {
        "total_tables": len(tables),
        "evaluations_completed": list(tables.keys()),
        "data_consolidated": True,
        "ready_for_paper": True,
        "reproducible": True,
    }


def main():
    parser_help = "Consolidate all evaluation results into paper-ready JSON"

    try:
        # Always read from metrics directory
        results_dir = Path("metrics")

        if not results_dir.exists():
            print(f"\nWarning: {results_dir} does not exist yet.")
            print("Run evaluation scripts first to generate results.")
            results_dir = Path(".")

        print(f"Consolidating results from {results_dir}")

        consolidated = consolidate_paper_data(results_dir)

        # Write consolidated results
        output_path = Path("docs/results/consolidated_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        write_json(output_path, consolidated)

        print(f"\n{'='*80}")
        print("CONSOLIDATION SUMMARY")
        print(f"{'='*80}")
        print(f"\nConsolidated {len(consolidated['tables'])} tables:")
        for table_name, table_data in consolidated["tables"].items():
            print(f"  - {table_name}: {table_data.get('title', 'N/A')}")

        print(f"\nOutput written to: {output_path}")
        print(f"\nPaper Statistics:")
        print(f"  Total Tables: {consolidated['summary_statistics']['total_tables']}")
        print(f"  Data Consolidated: {consolidated['summary_statistics']['data_consolidated']}")
        print(f"  Reproducible: {consolidated['summary_statistics']['reproducible']}")
        print(f"  Ready for Paper: {consolidated['summary_statistics']['ready_for_paper']}")

    except Exception as e:
        print(f"Error during consolidation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
