"""Evidence policy and reproducibility helpers for thesis evaluations."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.runtime.schemas import now_iso


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_EXECUTION_MODES = {"demo_no_ollama", "local_research", "evaluation_real"}
ALL_EXECUTION_MODES = REAL_EXECUTION_MODES
CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.json.gz"
SOURCE_MANIFEST_PATH = PROJECT_ROOT / "data" / "source_manifest.json"
SOURCE_ROOTS = ["backend", "services", "src", "scripts", "tests", "benchmarks", "deployment", "frontend"]
SOURCE_TOP_LEVEL = [
    ".dockerignore",
    ".env.example",
    ".gitignore",
    "compose.yaml",
    "requirements.txt",
    "requirements-research.txt",
    "run.ps1",
]
SOURCE_EXCLUDED_PARTS = {".next", "node_modules", "__pycache__", ".pytest_cache"}


def validate_execution_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized not in ALL_EXECUTION_MODES:
        allowed = ", ".join(sorted(ALL_EXECUTION_MODES))
        raise ValueError(f"Unknown execution mode '{mode}'. Expected one of: {allowed}")
    return normalized


def sha256_file(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


def build_experiment_manifest(
    *,
    run_id: str,
    execution_mode: str,
    benchmark_path: Path,
    config: Dict[str, Any],
    config_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    seed: Optional[int] = None,
    query_count: Optional[int] = None,
    max_latency_ms: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    git_state_at_start: Optional[Tuple[Optional[str], Optional[bool]]] = None,
) -> Dict[str, Any]:
    mode = validate_execution_mode(execution_mode)
    commit, dirty = git_state_at_start if git_state_at_start is not None else git_state()
    benchmark_sha256 = sha256_file(benchmark_path)
    config_sha256 = hashlib.sha256(
        json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    corpus_sha256 = sha256_file(CORPUS_PATH)
    snapshot_files, snapshot_sha256 = source_snapshot()
    provenance_ready = bool(
        mode == "evaluation_real"
        and benchmark_sha256
        and config_sha256
        and corpus_sha256
        and snapshot_sha256
    )
    ollama_enabled = bool(
        config.get("use_llm_router")
        or config.get("merge_llm_enabled")
        or config.get("force_merge_llm")
        or not config.get("lightweight_rag", True)
    )
    payload: Dict[str, Any] = {
        "schema_version": "1.1",
        "run_id": run_id,
        "git_commit": commit,
        "git_dirty": dirty,
        "git_state_scope": "experiment_start",
        "source_snapshot_sha256": snapshot_sha256,
        "source_snapshot_file_count": len(snapshot_files),
        "source_snapshot_files": snapshot_files,
        "timestamp": now_iso(),
        "execution_mode": mode,
        "evidence_type": "measured" if provenance_ready else "preliminary_measured",
        "provenance_ready": provenance_ready,
        "thesis_reporting_allowed": provenance_ready,
        "benchmark_file": relative_path(benchmark_path),
        "benchmark_sha256": benchmark_sha256,
        "query_count": query_count,
        "seed": seed,
        "cache_enabled": bool(config.get("cache_enabled", False)),
        "ollama_enabled": ollama_enabled,
        "database": database_label(),
        "frontend": "not involved",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or "not reported",
        "cpu_count": os.cpu_count(),
        "configuration_file": relative_path(config_path),
        "configuration_sha256": sha256_file(config_path),
        "configuration_payload_sha256": config_sha256,
        "corpus_file": relative_path(CORPUS_PATH),
        "corpus_sha256": corpus_sha256,
        "source_manifest_file": relative_path(SOURCE_MANIFEST_PATH),
        "source_manifest_sha256": sha256_file(SOURCE_MANIFEST_PATH),
        "manifest_file": relative_path(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "max_latency_ms": max_latency_ms,
        "config": config,
    }
    try:
        import psutil

        payload["memory_total_mb"] = round(psutil.virtual_memory().total / (1024 * 1024), 2)
    except Exception:
        payload["memory_total_mb"] = None
    payload["hardware"] = {
        "processor": payload["processor"],
        "cpu_count": payload["cpu_count"],
        "memory_total_mb": payload["memory_total_mb"],
        "platform": payload["platform"],
    }
    if extra:
        payload.update(extra)
    return payload


def source_snapshot() -> tuple[Dict[str, str], str]:
    paths: list[Path] = []
    for root_name in SOURCE_ROOTS:
        root = PROJECT_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or any(part in SOURCE_EXCLUDED_PARTS for part in path.parts):
                continue
            paths.append(path)
    for relative in SOURCE_TOP_LEVEL:
        path = PROJECT_ROOT / relative
        if path.is_file():
            paths.append(path)

    hashes = {
        relative_path(path) or str(path): sha256_file(path) or ""
        for path in sorted(set(paths), key=lambda value: relative_path(value) or str(value))
    }
    digest = hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return hashes, digest


def git_state() -> tuple[Optional[str], Optional[bool]]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return commit, bool(status.strip())
    except Exception:
        return None, None


def database_label() -> str:
    host = (os.getenv("PGHOST") or os.getenv("PG_HOST") or "localhost").lower()
    if "supabase" in host:
        return "Supabase PostgreSQL"
    if host in {"localhost", "127.0.0.1", "postgres"}:
        return "Local PostgreSQL"
    return "PostgreSQL (external host redacted)"
