"""
Master Evaluation Script - Run all evaluations and generate paper-ready output.

This script orchestrates the entire evaluation pipeline:
1. Router evaluation (3-model comparison)
2. RAG evaluation (3-version comparison)
3. SQL evaluation
4. Hybrid evaluation
5. System performance
6. Ablation study
7. Data consolidation

Usage:
    python -m src.evaluation.run_full_pipeline
    python src/evaluation/run_full_pipeline.py --dataset benchmarks/datasets/eval_90_queries.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def run_evaluation_script(script_name: str, args: List[str] = None) -> bool:
    """Run an evaluation script and return success status."""
    try:
        cmd = [sys.executable, "-m", f"src.evaluation.{script_name}"]
        if args:
            cmd.extend(args)

        print(f"\n{'='*80}")
        print(f"Running: {script_name}")
        print(f"{'='*80}")

        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run full evaluation pipeline")
    parser.add_argument(
        "--dataset",
        type=str,
        default="benchmarks/datasets/eval_90_queries.json",
        help="Path to query dataset",
    )
    parser.add_argument(
        "--skip-router",
        action="store_true",
        help="Skip router evaluation",
    )
    parser.add_argument(
        "--skip-rag",
        action="store_true",
        help="Skip RAG evaluation",
    )
    parser.add_argument(
        "--skip-sql",
        action="store_true",
        help="Skip SQL evaluation",
    )
    parser.add_argument(
        "--skip-hybrid",
        action="store_true",
        help="Skip hybrid evaluation",
    )
    parser.add_argument(
        "--skip-performance",
        action="store_true",
        help="Skip performance evaluation",
    )
    parser.add_argument(
        "--skip-ablation",
        action="store_true",
        help="Skip ablation study",
    )
    parser.add_argument(
        "--skip-consolidation",
        action="store_true",
        help="Skip data consolidation",
    )

    args = parser.parse_args()

    dataset_args = ["--dataset", args.dataset]

    print(f"\n{'*'*80}")
    print(f"QUERIONYX V3 - FULL EVALUATION PIPELINE")
    print(f"{'*'*80}")
    print(f"\nDataset: {args.dataset}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Table 1: Router Evaluation
    if not args.skip_router:
        results["router"] = run_evaluation_script("eval_router_final", dataset_args)
    else:
        print("\n[SKIPPED] Router evaluation")

    # Table 2: RAG Evaluation
    if not args.skip_rag:
        results["rag"] = run_evaluation_script("eval_rag_final", dataset_args)
    else:
        print("\n[SKIPPED] RAG evaluation")

    # Table 3: SQL Evaluation
    if not args.skip_sql:
        results["sql"] = run_evaluation_script("eval_sql_final", dataset_args)
    else:
        print("\n[SKIPPED] SQL evaluation")

    # Table 4: Hybrid Evaluation
    if not args.skip_hybrid:
        results["hybrid"] = run_evaluation_script("eval_hybrid_final", dataset_args)
    else:
        print("\n[SKIPPED] Hybrid evaluation")

    # Table 5: Performance Evaluation
    if not args.skip_performance:
        results["performance"] = run_evaluation_script("eval_performance", dataset_args)
    else:
        print("\n[SKIPPED] Performance evaluation")

    # Table 6: Ablation Study
    if not args.skip_ablation:
        results["ablation"] = run_evaluation_script("ablation_study", dataset_args)
    else:
        print("\n[SKIPPED] Ablation study")

    # Consolidate results
    if not args.skip_consolidation:
        results["consolidation"] = run_evaluation_script("consolidate_paper_data")
    else:
        print("\n[SKIPPED] Data consolidation")

    # Print summary
    print(f"\n{'='*80}")
    print("EVALUATION PIPELINE SUMMARY")
    print(f"{'='*80}\n")

    for evaluation, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{evaluation:20s}: {status}")

    all_passed = all(results.values())

    print(f"\n{'='*80}")
    if all_passed:
        print("✓ ALL EVALUATIONS COMPLETED SUCCESSFULLY")
        print("\nPaper-ready outputs:")
        print("  - docs/results/layer1_router_eval.md (Table 1)")
        print("  - docs/results/layer2_rag_eval.md (Table 2)")
        print("  - docs/results/layer2_sql_eval.md (Table 3)")
        print("  - docs/results/layer2_hybrid_eval.md (Table 4)")
        print("  - docs/results/layer3_performance.md (Table 5)")
        print("  - docs/results/ablation_study.md (Table 6)")
        print("  - docs/results/consolidated_results.json (Consolidated data)")
        print(f"\nConference: ICCCNET 2026")
        print(f"Status: Ready for submission")
    else:
        print("✗ SOME EVALUATIONS FAILED")
        print("\nFailed evaluations:")
        for evaluation, success in results.items():
            if not success:
                print(f"  - {evaluation}")

    print(f"{'='*80}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
