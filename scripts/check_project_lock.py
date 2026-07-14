"""Verify repository hygiene, frozen protocols, and thesis evidence status."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evidence import source_snapshot
from src.runtime.chunk_store import CHUNKS_FILE, load_chunks


REQUIRED_FILES = [
    ".dockerignore",
    ".env.example",
    "compose.yaml",
    "README.md",
    "requirements.txt",
    "requirements-research.txt",
    "data/README.md",
    "data/source_manifest.json",
    "docs/PROJECT_FREEZE.md",
    "docs/thesis_claim_evidence_matrix.md",
    "docs/evaluation/EVALUATION_POLICY.md",
    "docs/thesis_assets/README.md",
    "scripts/generate_thesis_assets.py",
    "src/evaluation/collect_baseline_outputs.py",
    "src/evaluation/collect_component_outputs.py",
    "src/evaluation/automatic_scoring.py",
    "benchmarks/references/eval_90_sql_references.json",
    "src/evaluation/evidence.py",
    "benchmarks/manifests/frozen_evaluation_sets.json",
    "data/processed/chunks_recursive.json.gz",
]

REMOVED_LEGACY_PATHS = [
    "WEEK8_EVALUATION_COMPLETE.md",
    "ablation",
    "data/processed/chunks_recursive.pkl",
    "data/test_queries",
    "docs/EVALUATION_PIPELINE.md",
    "docs/paper_assets",
    "docs/results",
    "docs/week3",
    "docs/week4",
    "docs/week5",
    "docs/week6",
    "docs/week7",
    "scripts/legacy",
    "src/evaluation/ablation_study.py",
    "src/evaluation/eval_baselines.py",
    "src/evaluation/eval_hybrid_final.py",
    "src/evaluation/eval_performance.py",
    "src/evaluation/eval_rag_final.py",
    "src/evaluation/eval_sql_final.py",
    "src/evaluation/export_paper_assets.py",
    "src/evaluation/run_full_pipeline.py",
]

FINAL_EVIDENCE_ARTIFACTS = {
    "final-answer-quality": (
        "reports/experiment_runs/final_90_full_v3/automatic_summary.json",
        "reports/experiment_runs/final_90_full_v3/manifest.json",
    ),
    "final-baseline": (
        "reports/experiment_runs/final_baseline_20/baseline_automatic_summary.json",
        "reports/experiment_runs/final_baseline_20/manifest.json",
    ),
    "final-components": (
        "reports/experiment_runs/final_component_hybrid_30/component_automatic_summary.json",
        "reports/experiment_runs/final_component_hybrid_30/manifest.json",
    ),
    "final-router-curated": (
        "reports/experiment_runs/final_router_curated_150/manifest.json",
        "reports/experiment_runs/final_router_curated_150/manifest.json",
    ),
    "final-router-stress": (
        "reports/experiment_runs/final_router_stress/manifest.json",
        "reports/experiment_runs/final_router_stress/manifest.json",
    ),
    "final-async": (
        "reports/experiment_runs/final_async_hybrid/async_automatic_summary.json",
        "reports/experiment_runs/final_async_hybrid/manifest.json",
    ),
}


def main() -> int:
    checks: list[tuple[str, str, str]] = []

    for relative in REQUIRED_FILES:
        path = PROJECT_ROOT / relative
        checks.append(("PASS" if path.exists() else "FAIL", f"required:{relative}", "present" if path.exists() else "missing"))

    remaining_legacy = [relative for relative in REMOVED_LEGACY_PATHS if (PROJECT_ROOT / relative).exists()]
    checks.append(
        (
            "FAIL" if remaining_legacy else "PASS",
            "legacy-artifacts-removed",
            ", ".join(remaining_legacy) if remaining_legacy else "no obsolete simulation/history paths",
        )
    )

    try:
        chunks = load_chunks()
        sources = {str(chunk.get("source")) for chunk in chunks}
        valid = len(chunks) == 9670 and len(sources) == 9
        checks.append(
            (
                "PASS" if valid else "FAIL",
                "chunk-corpus",
                f"{len(chunks)} chunks, {len(sources)} sources, {CHUNKS_FILE.stat().st_size / 1024 / 1024:.2f} MiB",
            )
        )
    except Exception as exc:
        checks.append(("FAIL", "chunk-corpus", str(exc)))

    render_yaml = read_text("deployment/render/render.yaml")
    checks.append(
        (
            "PASS" if "QUERIONYX_EXECUTION_MODE" in render_yaml and "demo_no_ollama" in render_yaml else "FAIL",
            "render-mode",
            "demo_no_ollama",
        )
    )

    runtime_requirements = read_text("requirements.txt").lower()
    heavy_runtime = [name for name in ["chromadb", "sentence-transformers", "langchain", "matplotlib", "ragas"] if name in runtime_requirements]
    checks.append(
        (
            "FAIL" if heavy_runtime else "PASS",
            "runtime-dependencies",
            ", ".join(heavy_runtime) if heavy_runtime else "research packages are separated",
        )
    )

    checks.extend(check_frozen_protocol())
    _, current_snapshot_sha256 = source_snapshot()
    for name, (relative, manifest_relative) in FINAL_EVIDENCE_ARTIFACTS.items():
        path = PROJECT_ROOT / relative
        manifest_path = PROJECT_ROOT / manifest_relative
        payload = load_json(path) if path.exists() else {}
        manifest = load_json(manifest_path) if manifest_path.exists() else {}
        snapshot_matches = manifest.get("source_snapshot_sha256") == current_snapshot_sha256
        reportable = (
            payload.get("thesis_reporting_allowed") is True
            and manifest.get("thesis_reporting_allowed") is True
            and snapshot_matches
        )
        if path.exists() and manifest_path.exists() and not snapshot_matches:
            detail = "stale source snapshot"
        else:
            detail = "reportable" if reportable else ("present but not reportable" if path.exists() else "pending")
        checks.append(
            (
                "PASS" if reportable else "WARN",
                name,
                detail,
            )
        )

    candidate_files = repository_files()
    candidate_size = sum(path.stat().st_size for path in candidate_files if path.is_file())
    checks.append(
        (
            "PASS" if candidate_size <= 25 * 1024 * 1024 else "FAIL",
            "clone-payload",
            f"{len(candidate_files)} files, {candidate_size / 1024 / 1024:.2f} MiB before Git compression",
        )
    )

    secret_findings = repository_secret_findings(candidate_files)
    checks.append(("FAIL" if secret_findings else "PASS", "repository-secrets", ", ".join(secret_findings) if secret_findings else "none detected"))

    failures = 0
    warnings = 0
    for status, name, detail in checks:
        print(f"[{status}] {name}: {detail}")
        failures += status == "FAIL"
        warnings += status == "WARN"

    print()
    if failures:
        print(f"Project lock FAILED with {failures} blocking issue(s).")
        return 1
    print(f"Project lock controls PASS with {warnings} pending research warning(s).")
    print("Pending evidence tasks remain listed in docs/PROJECT_FREEZE.md.")
    return 0


def check_frozen_protocol() -> list[tuple[str, str, str]]:
    path = PROJECT_ROOT / "benchmarks" / "manifests" / "frozen_evaluation_sets.json"
    if not path.exists():
        return [("FAIL", "frozen-protocol", "manifest missing")]

    payload = load_json(path)
    failures: list[str] = []
    corpus = payload.get("corpus") or {}
    if corpus:
        corpus_path = PROJECT_ROOT / corpus["path"]
        source_manifest = PROJECT_ROOT / corpus["source_manifest"]
        if not corpus_path.exists() or sha256(corpus_path) != corpus.get("sha256"):
            failures.append("corpus")
        if not source_manifest.exists() or sha256(source_manifest) != corpus.get("source_manifest_sha256"):
            failures.append("source_manifest")
    for name, dataset in (payload.get("datasets") or {}).items():
        source = PROJECT_ROOT / dataset["path"]
        if not source.exists() or sha256(source) != str(dataset.get("sha256") or "").lower():
            failures.append(name)

    for name, reference in (payload.get("automatic_references") or {}).items():
        source = PROJECT_ROOT / reference["path"]
        if not source.exists() or sha256(source) != str(reference.get("sha256") or "").lower():
            failures.append(f"reference:{name}")

    baseline = (payload.get("baseline_20") or {}).get("querionyx_config") or {}
    if baseline:
        source = PROJECT_ROOT / baseline["path"]
        if not source.exists() or sha256(source) != baseline["sha256"]:
            failures.append("baseline_20_config")

    components = (payload.get("component_hybrid_30") or {}).get("variant_configs") or {}
    for name, config in components.items():
        source = PROJECT_ROOT / config["path"]
        if not source.exists() or sha256(source) != config["sha256"]:
            failures.append(f"component:{name}")

    config_failures = []
    for config_path in sorted((PROJECT_ROOT / "benchmarks" / "configs").glob("*.json")):
        if load_json(config_path).get("execution_mode") != "evaluation_real":
            config_failures.append(config_path.name)
    failures.extend(config_failures)
    return [("FAIL" if failures else "PASS", "frozen-protocol", ", ".join(failures) if failures else "dataset, reference, and config hashes match")]


def repository_files() -> list[Path]:
    try:
        output = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except Exception:
        return []
    return [PROJECT_ROOT / relative for relative in output.splitlines() if (PROJECT_ROOT / relative).is_file()]


def repository_secret_findings(paths: list[Path]) -> list[str]:
    patterns = [
        ("huggingface-token", re.compile(r"hf_[A-Za-z0-9]{20,}")),
        ("embedded-postgres-password", re.compile(r"postgresql://[^\s:]+:[^\s@\[<]{8,}@")),
        (
            "assigned-secret",
            re.compile(
                r"(?im)^[ \t]*(?:PGPASSWORD|HF_TOKEN)[ \t]*=[ \t]*"
                r"(?!<|\[|your-|change-me|x{8,}[ \t]*$|$)[^\s#]{8,}"
            ),
        ),
    ]
    findings: list[str] = []
    for path in paths:
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        for label, pattern in patterns:
            if pattern.search(text):
                findings.append(f"{label}:{relative}")
    return findings


def read_text(relative: str) -> str:
    path = PROJECT_ROOT / relative
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
