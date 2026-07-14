"""Run and automatically score the frozen five-variant comparison."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.automatic_scoring import DEFAULT_REFERENCE_PATH
from src.evaluation.benchmark_runner import run_benchmark
from src.evaluation.evidence import build_experiment_manifest, git_state, sha256_file
from src.runtime.logging import write_json


FROZEN_SETS = PROJECT_ROOT / "benchmarks" / "manifests" / "frozen_evaluation_sets.json"
DEFAULT_RUN_MANIFEST = PROJECT_ROOT / "benchmarks" / "manifests" / "default_manifest.json"
VARIANT_CONFIGS = {
    "full_querionyx": PROJECT_ROOT / "benchmarks" / "configs" / "component_full.json",
    "dense_only": PROJECT_ROOT / "benchmarks" / "configs" / "component_dense_only.json",
    "rag_only": PROJECT_ROOT / "benchmarks" / "configs" / "component_rag_only.json",
    "sql_only": PROJECT_ROOT / "benchmarks" / "configs" / "component_sql_only.json",
    "no_fallback": PROJECT_ROOT / "benchmarks" / "configs" / "component_no_fallback.json",
}


def load_protocol() -> tuple[Path, List[str], Dict[str, Any]]:
    manifest = json.loads(FROZEN_SETS.read_text(encoding="utf-8"))
    protocol = manifest["component_hybrid_30"]
    if protocol["variants"] != list(VARIANT_CONFIGS):
        raise RuntimeError(
            f"Frozen component variants mismatch: expected {list(VARIANT_CONFIGS)}, got {protocol['variants']}"
        )
    for variant, config_path in VARIANT_CONFIGS.items():
        frozen_config = protocol["variant_configs"][variant]
        expected_path = (PROJECT_ROOT / frozen_config["path"]).resolve()
        if config_path.resolve() != expected_path or sha256_file(config_path) != frozen_config["sha256"]:
            raise RuntimeError(f"Component configuration does not match frozen protocol: {variant}")
    source = manifest["datasets"][protocol["source_dataset"]]
    dataset = PROJECT_ROOT / source["path"]
    actual_hash = sha256_file(dataset)
    if actual_hash != source["sha256"]:
        raise RuntimeError(
            f"Frozen component source hash mismatch: expected {source['sha256']}, got {actual_hash}"
        )
    return dataset, list(protocol["query_ids"]), manifest


def collect(output_dir: Path, max_latency_ms: int, seed: int) -> Dict[str, Any]:
    run_git_state = git_state()
    dataset, query_ids, _ = load_protocol()
    summaries: Dict[str, Any] = {}

    for variant, config in VARIANT_CONFIGS.items():
        variant_dir = output_dir / variant
        print(f"\n=== Component variant: {variant} ===")
        summaries[variant] = run_benchmark(
            dataset_path=dataset,
            config_path=config,
            manifest_path=DEFAULT_RUN_MANIFEST,
            output_dir=variant_dir,
            seed=seed,
            max_latency_ms=max_latency_ms,
            query_ids=query_ids,
            reference_path=DEFAULT_REFERENCE_PATH,
            git_state_at_start=run_git_state,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    root_manifest = build_experiment_manifest(
        run_id=output_dir.name,
        execution_mode="evaluation_real",
        benchmark_path=dataset,
        config={
            "config_name": "component_hybrid_30_automatic",
            "variants": {
                name: {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "sha256": sha256_file(path),
                }
                for name, path in VARIANT_CONFIGS.items()
            },
            "cache_enabled": False,
            "lightweight_rag": False,
            "use_llm_router": False,
            "merge_llm_enabled": False,
            "force_merge_llm": False,
        },
        seed=seed,
        query_count=len(query_ids),
        max_latency_ms=max_latency_ms,
        extra={
            "evaluation": "component_hybrid_30_automatic",
            "frozen_selection_manifest": str(FROZEN_SETS.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "frozen_selection_manifest_sha256": sha256_file(FROZEN_SETS),
            "query_ids": query_ids,
            "automatic_reference_file": str(DEFAULT_REFERENCE_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "automatic_reference_sha256": sha256_file(DEFAULT_REFERENCE_PATH),
            "scoring_method": "deterministic_reference_and_evidence_alignment",
        },
        git_state_at_start=run_git_state,
    )
    write_json(output_dir / "manifest.json", root_manifest)
    per_variant = {
        variant: {
            "query_count": summary["query_count"],
            "automatic_score": summary["automatic_score"],
            "automatic_pass_rate": summary["automatic_pass_rate"],
            "technical_pass_rate": summary["technical_pass_rate"],
            "mean_latency_ms": summary["latency"]["avg"],
            "sql_result_f1": summary["sql_result_f1"],
            "rag_evidence_score": summary["rag_evidence_score"],
            "hybrid_integration_score": summary["hybrid_integration_score"],
        }
        for variant, summary in summaries.items()
    }
    technical_summary = {
        "variant_count": len(VARIANT_CONFIGS),
        "query_count_per_variant": len(query_ids),
        "scoring_method": "deterministic_reference_and_evidence_alignment",
        "thesis_reporting_allowed": root_manifest["thesis_reporting_allowed"],
        "per_variant": per_variant,
    }
    write_json(
        output_dir / "component_automatic_summary.json",
        {
            "schema_version": "1.0",
            "artifact": "component_automatic_evaluation_summary",
            "evidence_type": root_manifest["evidence_type"],
            "thesis_reporting_allowed": root_manifest["thesis_reporting_allowed"],
            "scoring_method": technical_summary["scoring_method"],
            "reference_file": root_manifest["automatic_reference_file"],
            "reference_sha256": root_manifest["automatic_reference_sha256"],
            "summary": per_variant,
        },
    )
    return technical_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--max-latency-ms", type=int, default=15000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset, query_ids, _ = load_protocol()
    if args.dry_run:
        print(f"Frozen source: {dataset}")
        print(f"Source SHA-256: {sha256_file(dataset)}")
        print(f"Query IDs: {query_ids}")
        print(f"Variants: {list(VARIANT_CONFIGS)}")
        for name, path in VARIANT_CONFIGS.items():
            print(f"  {name}: {path} ({sha256_file(path)})")
        return 0

    output_dir = args.output_dir or (
        PROJECT_ROOT
        / "reports"
        / "experiment_runs"
        / f"{time.strftime('%Y%m%d_%H%M%S')}_component_hybrid_30"
    )
    result = collect(output_dir, args.max_latency_ms, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
