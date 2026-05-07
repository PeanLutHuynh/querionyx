"""Run 90-query UAT against the production /query endpoint."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from src.runtime.logging import write_json
from src.runtime.metrics import latency_summary


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_queries(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("queries", payload)


def post_query(endpoint: str, question: str, debug: bool = False) -> Dict[str, Any]:
    payload = json.dumps({"question": question, "debug": debug}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            data["_http_status"] = response.status
    except urllib.error.HTTPError as exc:
        data = {"error": exc.read().decode("utf-8", errors="replace"), "_http_status": exc.code}
    except Exception as exc:
        data = {"error": str(exc), "_http_status": None}
    data["_client_latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return data


def run_uat(dataset: Path, endpoint: str, output_dir: Path, repeat_cache_check: int = 10) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    queries = load_queries(dataset)
    cache_repeat_questions = queries[: max(0, repeat_cache_check)]

    for idx, case in enumerate(queries, start=1):
        response = post_query(endpoint, case["question"], debug=False)
        rows.append(_row(case, response, idx, repeated=False))
        print(f"[{idx}/{len(queries)}] status={rows[-1]['http_status']} intent={rows[-1]['intent']} cache={rows[-1]['cache_hit']} trace={rows[-1]['trace_id']}")

    for repeat_idx, case in enumerate(cache_repeat_questions, start=1):
        response = post_query(endpoint, case["question"], debug=False)
        rows.append(_row(case, response, len(rows) + 1, repeated=True))
        print(f"[cache {repeat_idx}/{len(cache_repeat_questions)}] status={rows[-1]['http_status']} cache={rows[-1]['cache_hit']} latency={rows[-1]['latency_ms']}")

    summary = _summary(rows)
    write_json(output_dir / "uat_results.json", {"summary": summary, "rows": rows})
    _write_csv(output_dir / "uat_results.csv", rows)
    return summary


def _row(case: Dict[str, Any], response: Dict[str, Any], idx: int, repeated: bool) -> Dict[str, Any]:
    return {
        "row_id": idx,
        "query_id": case.get("query_id") or case.get("id"),
        "question": case.get("question"),
        "expected_intent": case.get("expected_intent") or case.get("ground_truth_intent"),
        "http_status": response.get("_http_status"),
        "error": response.get("error"),
        "answer_nonempty": bool(str(response.get("answer") or "").strip()),
        "latency_ms": response.get("latency_ms"),
        "client_latency_ms": response.get("_client_latency_ms"),
        "intent": response.get("intent"),
        "cache_hit": response.get("cache_hit"),
        "router_type": response.get("router_type_used"),
        "hybrid_branch_usage": ",".join(response.get("branches") or []),
        "trace_id": response.get("trace_id"),
        "timeout_triggered": response.get("timeout_triggered"),
        "fallback_used": response.get("fallback_used"),
        "repeated": repeated,
    }


def _summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    noncrash = [row for row in rows if row["http_status"] == 200 and not row["error"]]
    nonempty = [row for row in rows if row["answer_nonempty"]]
    cache_hits = [row for row in rows if row["cache_hit"] is True]
    timeouts = [row for row in rows if row["timeout_triggered"] is True]
    latency = latency_summary(row["latency_ms"] for row in rows if row.get("latency_ms") is not None)
    return {
        "total_requests": total,
        "non_crash_rate": round(len(noncrash) / total, 4) if total else 0.0,
        "non_empty_rate": round(len(nonempty) / total, 4) if total else 0.0,
        "timeout_rate": round(len(timeouts) / total, 4) if total else 0.0,
        "cache_hit_rate": round(len(cache_hits) / total, 4) if total else 0.0,
        "latency": latency,
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Querionyx V3 UAT against /query.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/query")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "experiment_runs" / "week7_uat_90")
    parser.add_argument("--repeat-cache-check", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run_uat(args.dataset, args.endpoint, args.output_dir, args.repeat_cache_check)
    print(json.dumps(result, ensure_ascii=False, indent=2))

