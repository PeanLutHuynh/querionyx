"""Audit benchmark readiness for the no-Ollama Render demo.

This script intentionally avoids database, embedding, and LLM calls. It checks:
- router prediction vs. benchmark intent;
- whether SQL/HYBRID questions have deterministic SQL fast paths;
- whether annual-report questions mention a known company.

Use it before demos to find gaps that should be fixed with router keywords,
SQL fast paths, or RAG topic terms rather than response-cache memorization.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(PROJECT_ROOT))

from src.router.rule_based_router import RuleBasedRouter
from src.sql.text_to_sql import TextToSQLPipeline


DEFAULT_DATASET = PROJECT_ROOT / "data" / "test_queries" / "eval_150_queries.json"


def load_queries(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    queries = payload.get("queries", payload)
    if not isinstance(queries, list):
        raise ValueError(f"Unsupported dataset shape: {path}")
    return [item for item in queries if isinstance(item, dict) and item.get("question")]


def company_mentions(question: str) -> List[str]:
    q = question.lower()
    return [company for company in ("fpt", "vinamilk", "masan") if company in q]


def audit(queries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    router = RuleBasedRouter()
    sql_planner = TextToSQLPipeline.__new__(TextToSQLPipeline)
    rows: List[Dict[str, Any]] = []
    counters: Counter[str] = Counter()

    for item in queries:
        question = str(item["question"]).strip()
        expected = str(item.get("ground_truth_intent") or item.get("intent") or "").upper()
        route = router.classify(question)
        predicted = route.intent.upper()
        fast_sql = sql_planner._generate_fast_sql(question)
        companies = company_mentions(question)

        needs_sql = expected in {"SQL", "HYBRID"} or predicted in {"SQL", "HYBRID"}
        annual_report = str(item.get("source_hint") or "").lower() in {"annual_reports", "annual_report"}
        no_ollama_safe = True
        issues: List[str] = []

        if expected and predicted != expected:
            issues.append("route_mismatch")
        if needs_sql and not fast_sql:
            no_ollama_safe = False
            issues.append("missing_sql_fast_path")
        if annual_report and not companies:
            issues.append("rag_missing_company_signal")

        if not issues:
            issues.append("ok")

        counters["total"] += 1
        counters[f"expected_{expected or 'UNKNOWN'}"] += 1
        counters[f"predicted_{predicted}"] += 1
        if predicted == expected:
            counters["route_correct"] += 1
        if needs_sql:
            counters["needs_sql"] += 1
        if fast_sql:
            counters["sql_fast_path"] += 1
        if no_ollama_safe:
            counters["no_ollama_safe"] += 1
        for issue in issues:
            counters[f"issue_{issue}"] += 1

        rows.append(
            {
                "id": item.get("id"),
                "question": question,
                "expected": expected,
                "predicted": predicted,
                "confidence": route.confidence,
                "matched_sql": route.matched_sql_keywords,
                "matched_rag": route.matched_rag_keywords,
                "has_sql_fast_path": bool(fast_sql),
                "companies": companies,
                "no_ollama_safe": no_ollama_safe,
                "issues": [issue for issue in issues if issue != "ok"],
                "sql": fast_sql or "",
            }
        )

    total = counters["total"] or 1
    route_correct = counters["route_correct"]
    summary = {
        "total": counters["total"],
        "route_accuracy": round(route_correct / total, 4),
        "no_ollama_safe_rate": round(counters["no_ollama_safe"] / total, 4),
        "needs_sql": counters["needs_sql"],
        "sql_fast_path": counters["sql_fast_path"],
        "issues": {
            key.replace("issue_", ""): value
            for key, value in sorted(counters.items())
            if key.startswith("issue_") and key != "issue_ok"
        },
        "expected_counts": {
            key.replace("expected_", ""): value
            for key, value in sorted(counters.items())
            if key.startswith("expected_")
        },
        "predicted_counts": {
            key.replace("predicted_", ""): value
            for key, value in sorted(counters.items())
            if key.startswith("predicted_")
        },
    }
    return {"summary": summary, "rows": rows}


def write_markdown(report: Dict[str, Any], output: Path) -> None:
    summary = report["summary"]
    rows = report["rows"]
    risky = [row for row in rows if row["issues"] or not row["no_ollama_safe"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# No-Ollama Demo Readiness Audit",
        "",
        "## Summary",
        "",
        f"- Total queries: {summary['total']}",
        f"- Router accuracy: {summary['route_accuracy']:.2%}",
        f"- No-Ollama safe rate: {summary['no_ollama_safe_rate']:.2%}",
        f"- Queries needing SQL branch: {summary['needs_sql']}",
        f"- Queries with SQL fast path: {summary['sql_fast_path']}",
        f"- Issues: `{json.dumps(summary['issues'], ensure_ascii=False)}`",
        "",
        "## Risky Queries",
        "",
        "| ID | Expected | Predicted | Fast SQL | Issues | Question |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in risky[:80]:
        issues = ", ".join(row["issues"]) or "-"
        fast = "yes" if row["has_sql_fast_path"] else "no"
        question = str(row["question"]).replace("|", "\\|")
        lines.append(f"| {row['id']} | {row['expected']} | {row['predicted']} | {fast} | {issues} | {question} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json-output", type=Path, default=PROJECT_ROOT / "reports" / "experiment_runs" / "no_ollama_readiness.json")
    parser.add_argument("--markdown-output", type=Path, default=PROJECT_ROOT / "docs" / "evaluation" / "no_ollama_readiness.md")
    args = parser.parse_args()

    report = audit(load_queries(args.dataset))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
