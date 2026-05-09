"""Integration smoke test for QueryonixPipelineV3.

Runs 9 examples from eval_90_queries.json: 3 RAG, 3 SQL, 3 HYBRID.
The goal is functional safety and latency logging, not final answer grading.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline_v3 import QueryonixPipelineV3

TEST_SET = PROJECT_ROOT / "data" / "test_queries" / "eval_150_queries.json"


def load_cases(path: Path = TEST_SET) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    queries = payload.get("queries", payload)
    selected: List[Dict[str, Any]] = []
    for intent in ["RAG", "SQL", "HYBRID"]:
        selected.extend([q for q in queries if q.get("ground_truth_intent") == intent][:3])
    return selected


def run(max_latency_ms: int = 15000) -> List[Dict[str, Any]]:
    pipeline = QueryonixPipelineV3(max_total_latency_ms=max_latency_ms)
    cases = load_cases()
    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(cases, start=1):
        question = item["question"]
        try:
            output = pipeline.query(question)
            passed = bool(output.get("answer")) and output.get("latency_ms", 999999) <= max_latency_ms
            error = None
        except Exception as exc:
            output = {}
            passed = False
            error = str(exc)

        row = {
            "id": item.get("id"),
            "expected_intent": item.get("ground_truth_intent"),
            "question": question,
            "passed": passed,
            "error": error,
            "intent": output.get("intent"),
            "total_latency_ms": output.get("latency_ms"),
            "router_type_used": output.get("router_type_used"),
            "llm_call_count": output.get("llm_call_count"),
            "branches": output.get("branches"),
            "answer_preview": (output.get("answer") or "")[:160],
        }
        results.append(row)

        status = "OK" if passed else "FAIL"
        print(
            f"[{idx}/9] {status} {row['id']} intent={row['intent']} "
            f"latency={row['total_latency_ms']}ms router={row['router_type_used']} "
            f"llm_calls={row['llm_call_count']} branches={row['branches']}"
        )

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run QueryonixPipelineV3 integration smoke test.")
    parser.add_argument("--max-latency-ms", type=int, default=15000)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "docs" / "week6_integration_test_v3.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    results = run(max_latency_ms=args.max_latency_ms)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [row for row in results if not row["passed"]]
    print(f"\nWrote {args.output}")
    if failures:
        raise SystemExit(1)
