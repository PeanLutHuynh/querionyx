"""Router stress testing for Querionyx V3."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline_v3 import AdaptiveRouter
from src.runtime.logging import write_csv, write_json
from src.runtime.metrics import latency_summary


def load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("queries", payload)


def expected_intent(case: Dict[str, Any]) -> str:
    return str(case.get("expected_intent") or case.get("ground_truth_intent") or "").upper()


def run_router_stress(dataset: Path, output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    router = AdaptiveRouter(use_llm_for_ambiguous=False)
    rows = []
    for idx, case in enumerate(load_cases(dataset), start=1):
        started = time.perf_counter()
        result = router.classify(case["question"])
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        expected = expected_intent(case)
        actual = result["intent"]
        correct = expected == actual
        confidence = float(result.get("confidence") or 0.0)
        rows.append(
            {
                "query_id": case.get("query_id") or case.get("id") or f"router_{idx:04d}",
                "question": case["question"],
                "expected_intent": expected,
                "actual_intent": actual,
                "correct": correct,
                "confidence": confidence,
                "calibration_error": abs(confidence - (1.0 if correct else 0.0)),
                "latency_ms": latency_ms,
                "router_type": result.get("router_type_used", "adaptive_rule_or_rule"),
                "reason": result.get("reason", ""),
            }
        )
    total = len(rows)
    wrong = [row for row in rows if not row["correct"]]
    summary = {
        "dataset": str(dataset),
        "query_count": total,
        "router_accuracy": round((total - len(wrong)) / total, 4) if total else 0.0,
        "misrouting_rate": round(len(wrong) / total, 4) if total else 0.0,
        "confidence_calibration_error": round(sum(row["calibration_error"] for row in rows) / total, 4) if total else 0.0,
        "latency": latency_summary(row["latency_ms"] for row in rows),
        "misrouting_cases": wrong,
    }
    write_json(output_dir / "router_stress_summary.json", summary)
    write_json(PROJECT_ROOT / "metrics" / "latency" / "router_stress_summary.json", summary)
    write_csv(output_dir / "router_stress_rows.csv", rows)
    write_csv(output_dir / "router_misrouting_cases.csv", wrong)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run router stress test.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "router_ambiguity_cases.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "experiment_runs" / "week7_router_stress")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(run_router_stress(args.dataset, args.output_dir), ensure_ascii=False, indent=2))
