"""Evaluate the Week 5 Text-to-SQL pipeline on Northwind questions.

The evaluator never gives reference SQL or expected answers to the pipeline.
Reference SQL is used only after generation for exact-match and error analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEST_SET = PROJECT_ROOT / "data" / "test_queries" / "sql_queries.json"
DEFAULT_OUTPUT_MARKDOWN = PROJECT_ROOT / "docs" / "eval_sql_module.md"

sys.path.insert(0, str(PROJECT_ROOT))

from src.sql.text_to_sql import SQLResult, TextToSQLPipeline


AGG_KEYWORDS = {"count", "sum", "avg", "min", "max"}


def normalize_sql(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = sql.strip().rstrip(";").lower()
    return re.sub(r"\s+", " ", sql)


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key).lower(): normalize_value(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return round(float(value), 4)
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, str):
        return value.strip()
    return value


def parse_expected_answer(raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def rows_as_comparable(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_value(row) for row in rows]


def results_match(expected_raw: Any, actual_rows: List[Dict[str, Any]]) -> bool:
    expected = normalize_value(parse_expected_answer(expected_raw))
    actual = rows_as_comparable(actual_rows)

    if isinstance(expected, list):
        return sorted(expected, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True)) == sorted(
            actual,
            key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True),
        )

    if isinstance(expected, dict) and len(actual) == 1:
        return expected == actual[0]

    return expected == actual


def has_join(sql: str) -> bool:
    return bool(re.search(r"\bjoin\b", sql, flags=re.IGNORECASE))


def has_aggregation(sql: str) -> bool:
    lowered = sql.lower()
    return any(re.search(rf"\b{keyword}\s*\(", lowered) for keyword in AGG_KEYWORDS) or " group by " in f" {lowered} "


def classify_error(expected_sql: str, generated_sql: str, error_message: Optional[str]) -> str:
    expected_lower = expected_sql.lower()
    generated_lower = generated_sql.lower()

    if error_message:
        msg = error_message.lower()
        if "column" in msg and "does not exist" in msg:
            return "wrong_column"
        if "relation" in msg and "does not exist" in msg:
            return "wrong_column"
        if "missing from-clause entry" in msg or "invalid reference" in msg:
            return "wrong_join"
        if "aggregate" in msg or "group by" in msg:
            return "wrong_aggregation"

    if has_join(expected_lower) and not has_join(generated_lower):
        return "wrong_join"
    if has_aggregation(expected_lower) and not has_aggregation(generated_lower):
        return "wrong_aggregation"
    return "other"


def load_queries(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        return payload.get("queries", [])
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Unsupported test-set format in {path}")


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def truncate(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_report(
    rows: List[Dict[str, Any]],
    test_set: Path,
    model_name: str,
    elapsed_seconds: float,
) -> str:
    total = len(rows)
    exec_success = sum(1 for row in rows if row["execution_ok"] and row["matches_answer"])
    exact_match = sum(1 for row in rows if row["exact_match"])
    retry_count = sum(1 for row in rows if row["retries"] > 0)

    error_breakdown = {"wrong_join": 0, "wrong_column": 0, "wrong_aggregation": 0, "other": 0}
    for row in rows:
        if not (row["execution_ok"] and row["matches_answer"]):
            error_breakdown[row["error_type"]] += 1

    execution_accuracy = exec_success / total if total else 0.0
    exact_match_rate = exact_match / total if total else 0.0
    retry_rate = retry_count / total if total else 0.0

    lines = [
        "# Text-to-SQL Module - Evaluation Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d')}",
        f"**Model:** `{model_name}`",
        f"**Test set:** `{test_set.relative_to(PROJECT_ROOT)}`",
        f"**Total queries:** {total}",
        f"**Elapsed:** {elapsed_seconds:.1f}s",
        "",
        "## Methodology",
        "",
        "- The pipeline receives only the natural-language question and schema-linked database context.",
        "- Reference SQL is used only after generation for exact-match scoring and error classification.",
        "- Execution accuracy requires generated SQL to run without error and match `expected_answer`.",
        "- Empty results are accepted as final results and are not retried by the pipeline.",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Execution Accuracy | {execution_accuracy:.3f} |",
        f"| Exact Match (SQL) | {exact_match_rate:.3f} |",
        f"| Retry Rate | {retry_rate:.3f} |",
        "",
        "## Error Analysis",
        "",
        "| Error Type | Count |",
        "|---|---:|",
        f"| wrong_join | {error_breakdown['wrong_join']} |",
        f"| wrong_column | {error_breakdown['wrong_column']} |",
        f"| wrong_aggregation | {error_breakdown['wrong_aggregation']} |",
        f"| other | {error_breakdown['other']} |",
        "",
        "## Detailed Results",
        "",
        "| ID | Exec OK | Answer Match | Exact SQL | Retries | Cache | Error Type | Total (ms) | LLM (ms) | DB (ms) | Generated SQL | Error |",
        "|---|---|---|---|---:|---:|---|---:|---:|---:|---|---|",
    ]

    for row in rows:
        lines.append(
            "| {id} | {execution_ok} | {matches_answer} | {exact_match} | {retries} | {cache_hit} | {error_type} | {latency_ms} | {llm_ms} | {db_ms} | `{sql}` | {error} |".format(
                id=markdown_escape(row["id"]),
                execution_ok="Y" if row["execution_ok"] else "N",
                matches_answer="Y" if row["matches_answer"] else "N",
                exact_match="Y" if row["exact_match"] else "N",
                retries=row["retries"],
                cache_hit="Y" if row.get("timings", {}).get("sql_cache_hit") == 1.0 else "N",
                error_type=markdown_escape(row["error_type"] or "-"),
                latency_ms=row["latency_ms"],
                llm_ms=row.get("timings", {}).get("llm_sql_ms", "-"),
                db_ms=row.get("timings", {}).get("db_ms", "-"),
                sql=markdown_escape(truncate(row["generated_sql"])),
                error=markdown_escape(truncate(row.get("error") or "-", 120)),
            )
        )

    return "\n".join(lines)


def evaluate(
    test_set: Path = DEFAULT_TEST_SET,
    output_markdown: Path = DEFAULT_OUTPUT_MARKDOWN,
    start: int = 0,
    limit: Optional[int] = None,
    sample_row_limit: int = 3,
    max_tables: int = 3,
    timeout_seconds: Optional[int] = None,
    num_predict: Optional[int] = None,
    max_result_rows: int = 500,
) -> List[Dict[str, Any]]:
    sql_model = os.getenv("OLLAMA_SQL_MODEL", "qwen2.5:3b")
    pipeline = TextToSQLPipeline(
        sql_model=sql_model,
        nl_model=os.getenv("OLLAMA_SQL_NL_MODEL", sql_model),
        max_retries=2,
        llm_timeout_seconds=timeout_seconds or int(os.getenv("OLLAMA_SQL_TIMEOUT", "60")),
        sample_row_limit=sample_row_limit,
        max_tables=max_tables,
        sql_num_predict=num_predict,
        max_result_rows=max_result_rows,
    )

    queries = load_queries(test_set)
    if start:
        queries = queries[start:]
    if limit is not None:
        queries = queries[:limit]

    rows: List[Dict[str, Any]] = []
    started = time.time()
    total = len(queries)

    for idx, item in enumerate(queries, start=1):
        question = item.get("question", "")
        expected_sql = item.get("expected_sql", "")
        expected_answer = item.get("expected_answer", "")

        query_started = time.time()
        try:
            output = pipeline.query(question, include_nl_answer=False)
            result = SQLResult(
                sql=output["sql_query"],
                rows=output["rows"],
                error=output["error"],
                retries=output["retries"],
                timings=output["timings"],
                nl_answer=output.get("nl_answer", ""),
                relevant_tables=output.get("relevant_tables", []),
                relevant_columns=output.get("relevant_columns", []),
            )
        except Exception as exc:
            result = SQLResult(sql="", rows=[], error=str(exc), retries=0)
        elapsed_ms = round((time.time() - query_started) * 1000, 2)

        generated_sql = result.sql.strip()
        execution_ok = result.error is None
        matches_answer = execution_ok and results_match(expected_answer, result.rows)
        exact_sql = normalize_sql(generated_sql) == normalize_sql(expected_sql)
        error_type = None if execution_ok and matches_answer else classify_error(expected_sql, generated_sql, result.error)

        rows.append(
            {
                "id": item.get("id", f"query_{idx}"),
                "question": question,
                "expected_sql": expected_sql,
                "generated_sql": generated_sql,
                "execution_ok": execution_ok,
                "matches_answer": matches_answer,
                "exact_match": exact_sql,
                "retries": result.retries,
                "error": result.error,
                "error_type": error_type,
                "latency_ms": elapsed_ms,
                "timings": result.timings or {},
            }
        )

        status = "OK" if execution_ok and matches_answer else "FAIL"
        llm_ms = (result.timings or {}).get("llm_sql_ms", "-")
        db_ms = (result.timings or {}).get("db_ms", "-")
        print(
            f"[{idx}/{total}] {status} {item.get('id')} "
            f"retries={result.retries} total={elapsed_ms}ms llm={llm_ms}ms db={db_ms}ms"
        )

    report = build_report(rows, test_set, sql_model, time.time() - started)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(report, encoding="utf-8")
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the Text-to-SQL pipeline.")
    parser.add_argument("--test-set", type=Path, default=DEFAULT_TEST_SET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_MARKDOWN)
    parser.add_argument("--start", type=int, default=0, help="Skip the first N queries before evaluating.")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N queries.")
    parser.add_argument("--sample-row-limit", type=int, default=3)
    parser.add_argument("--max-tables", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=None, help="Ollama request timeout in seconds.")
    parser.add_argument("--num-predict", type=int, default=None, help="Maximum SQL tokens generated by Ollama.")
    parser.add_argument("--max-result-rows", type=int, default=500)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate(
        test_set=args.test_set,
        output_markdown=args.output,
        start=args.start,
        limit=args.limit,
        sample_row_limit=args.sample_row_limit,
        max_tables=args.max_tables,
        timeout_seconds=args.timeout,
        num_predict=args.num_predict,
        max_result_rows=args.max_result_rows,
    )
    print(f"\nReport written to {args.output}")
