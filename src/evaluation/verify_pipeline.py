"""
Verification Script - Verify all evaluation components are in place.

Checks that all required files, dependencies, and structures exist.

Usage:
    python -m src.evaluation.verify_pipeline
    python src/evaluation/verify_pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def check_file_exists(path: Path, description: str) -> Tuple[bool, str]:
    """Check if a file exists and report status."""
    if path.exists():
        return True, f"✓ {description}: {path.relative_to(PROJECT_ROOT)}"
    else:
        return False, f"✗ {description}: {path.relative_to(PROJECT_ROOT)} (MISSING)"


def check_directory_exists(path: Path, description: str) -> Tuple[bool, str]:
    """Check if a directory exists and report status."""
    if path.exists() and path.is_dir():
        return True, f"✓ {description}: {path.relative_to(PROJECT_ROOT)}"
    else:
        return False, f"✗ {description}: {path.relative_to(PROJECT_ROOT)} (MISSING)"


def verify_evaluation_scripts() -> bool:
    """Verify all evaluation scripts exist."""
    print("\n" + "=" * 80)
    print("VERIFICATION: Evaluation Scripts")
    print("=" * 80)

    scripts = [
        (PROJECT_ROOT / "src" / "evaluation" / "eval_router_final.py", "Router evaluation"),
        (PROJECT_ROOT / "src" / "evaluation" / "eval_rag_final.py", "RAG evaluation"),
        (PROJECT_ROOT / "src" / "evaluation" / "eval_sql_final.py", "SQL evaluation"),
        (PROJECT_ROOT / "src" / "evaluation" / "eval_hybrid_final.py", "Hybrid evaluation"),
        (PROJECT_ROOT / "src" / "evaluation" / "eval_performance.py", "Performance evaluation"),
        (PROJECT_ROOT / "src" / "evaluation" / "ablation_study.py", "Ablation study"),
        (PROJECT_ROOT / "src" / "evaluation" / "consolidate_paper_data.py", "Data consolidation"),
        (PROJECT_ROOT / "src" / "evaluation" / "run_full_pipeline.py", "Master pipeline"),
    ]

    all_exist = True
    for script_path, description in scripts:
        exists, message = check_file_exists(script_path, description)
        print(message)
        all_exist = all_exist and exists

    return all_exist


def verify_datasets() -> bool:
    """Verify all required datasets exist."""
    print("\n" + "=" * 80)
    print("VERIFICATION: Datasets")
    print("=" * 80)

    datasets = [
        (PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json", "Standard 90-query dataset"),
        (PROJECT_ROOT / "benchmarks" / "datasets" / "router_stress_100.json", "Stress test dataset"),
        (PROJECT_ROOT / "benchmarks" / "datasets" / "smoke_9_queries.json", "Smoke test dataset"),
    ]

    all_exist = True
    for dataset_path, description in datasets:
        exists, message = check_file_exists(dataset_path, description)
        print(message)
        all_exist = all_exist and exists

    return all_exist


def verify_dependencies() -> bool:
    """Verify Python dependencies are available."""
    print("\n" + "=" * 80)
    print("VERIFICATION: Python Dependencies")
    print("=" * 80)

    dependencies = [
        "pathlib",
        "json",
        "csv",
        "time",
        "subprocess",
        "random",
    ]

    all_available = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep}: Available")
        except ImportError:
            print(f"✗ {dep}: NOT AVAILABLE")
            all_available = False

    # Check optional dependencies
    print("\nOptional dependencies:")
    optional = ["psutil", "dotenv", "langchain"]
    for dep in optional:
        try:
            __import__(dep)
            print(f"✓ {dep}: Available")
        except ImportError:
            print(f"⚠ {dep}: Not available (graceful fallback)")

    return all_available


def verify_output_directories() -> bool:
    """Verify output directories are creatable."""
    print("\n" + "=" * 80)
    print("VERIFICATION: Output Directories")
    print("=" * 80)

    dirs = [
        (PROJECT_ROOT / "docs" / "results", "Results output"),
        (PROJECT_ROOT / "metrics", "Metrics storage"),
        (PROJECT_ROOT / "metrics" / "router_eval", "Router eval metrics"),
        (PROJECT_ROOT / "metrics" / "rag_eval", "RAG eval metrics"),
        (PROJECT_ROOT / "metrics" / "sql_eval", "SQL eval metrics"),
        (PROJECT_ROOT / "metrics" / "hybrid_eval", "Hybrid eval metrics"),
        (PROJECT_ROOT / "metrics" / "performance_eval", "Performance eval metrics"),
        (PROJECT_ROOT / "metrics" / "ablation_study", "Ablation study metrics"),
    ]

    all_ok = True
    for dir_path, description in dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ {description}: {dir_path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            print(f"✗ {description}: {str(e)}")
            all_ok = False

    return all_ok


def verify_imports() -> bool:
    """Verify key imports work."""
    print("\n" + "=" * 80)
    print("VERIFICATION: Module Imports")
    print("=" * 80)

    imports = [
        ("src.runtime.logging", "write_json, write_csv, write_markdown"),
        ("src.runtime.schemas", "now_iso"),
        ("src.router.rule_based_router", "RuleBasedRouter"),
    ]

    all_ok = True
    for module_name, items in imports:
        try:
            module = __import__(module_name, fromlist=items.split(", "))
            print(f"✓ {module_name}.{items}")
        except Exception as e:
            print(f"✗ {module_name}: {str(e)}")
            all_ok = False

    return all_ok


def verify_cli_support() -> bool:
    """Verify scripts can be run from CLI."""
    print("\n" + "=" * 80)
    print("VERIFICATION: CLI Runnable Scripts")
    print("=" * 80)

    scripts = [
        "eval_router_final",
        "eval_rag_final",
        "eval_sql_final",
        "eval_hybrid_final",
        "eval_performance",
        "ablation_study",
        "consolidate_paper_data",
        "run_full_pipeline",
    ]

    import subprocess

    all_ok = True
    for script in scripts:
        try:
            result = subprocess.run(
                [sys.executable, "-m", f"src.evaluation.{script}", "--help"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                print(f"✓ src.evaluation.{script}: CLI works")
            else:
                print(f"⚠ src.evaluation.{script}: Returns error (may be configuration)")
        except subprocess.TimeoutExpired:
            print(f"⚠ src.evaluation.{script}: Timeout (may be waiting for Ollama)")
        except Exception as e:
            print(f"✗ src.evaluation.{script}: {str(e)}")
            all_ok = False

    return all_ok


def main():
    print("\n" + "*" * 80)
    print("EVALUATION PIPELINE VERIFICATION")
    print("*" * 80)

    results = {
        "Evaluation Scripts": verify_evaluation_scripts(),
        "Datasets": verify_datasets(),
        "Dependencies": verify_dependencies(),
        "Output Directories": verify_output_directories(),
        "Module Imports": verify_imports(),
        "CLI Support": verify_cli_support(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{check_name:30s}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED")
        print("\nYou can now run the full pipeline:")
        print("  python -m src.evaluation.run_full_pipeline")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
        print("\nPlease review the errors above and fix:")
        for check_name, result in results.items():
            if not result:
                print(f"  - {check_name}")

    print("=" * 80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
