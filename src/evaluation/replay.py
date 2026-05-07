"""Replay a saved Querionyx benchmark manifest."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_runner import run_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay a previous Querionyx experiment run.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import json

    manifest = json.loads((args.run_dir / "manifest.json").read_text(encoding="utf-8"))
    output = args.output_dir or PROJECT_ROOT / "reports" / "experiment_runs" / f"{time.strftime('%Y%m%d_%H%M%S')}_replay"
    config_path = args.run_dir / "ablation_config.json"
    run_benchmark(
        Path(manifest["dataset"]),
        config_path if config_path.exists() else None,
        None,
        output,
        int(manifest["seed"]),
        int(manifest["max_latency_ms"]),
        None,
    )
