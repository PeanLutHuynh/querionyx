"""Deterministic, reference-backed scoring for the frozen 90-query benchmark.

The score measures routing, SQL result equivalence, document-source alignment,
topic evidence coverage, and hybrid integration. It does not use an LLM judge
or claim unrestricted free-form semantic correctness.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import psycopg2
from dotenv import load_dotenv

from src.runtime.fallbacks import INSUFFICIENT_EVIDENCE


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_PATH = PROJECT_ROOT / "benchmarks" / "references" / "eval_90_sql_references.json"
PASS_THRESHOLD = 0.70

STOPWORDS = {
    "bao", "cao", "cua", "cho", "cong", "duoc", "giai", "hoat", "la", "mo", "mot",
    "nao", "nhu", "nhung", "noi", "ra", "sao", "the", "thi", "trinh", "trong", "ve",
    "what", "which", "with", "from", "report", "annual", "tim", "thuong", "nien",
    "fpt", "masan", "vinamilk", "rag", "sql",
}


class AutomaticScorer:
    def __init__(self, reference_path: Path = DEFAULT_REFERENCE_PATH):
        payload = json.loads(reference_path.read_text(encoding="utf-8-sig"))
        self.reference_path = reference_path
        self.templates: Dict[str, str] = payload["templates"]
        self.case_templates: Dict[str, str] = payload["cases"]
        self._reference_rows: Dict[str, list[dict[str, Any]]] = {}
        self._connection = None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def score(self, case: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        case_id = str(case.get("id") or case.get("query_id") or "")
        expected_intent = str(case.get("ground_truth_intent") or case.get("expected_intent") or "").upper()
        actual_intent = str(output.get("intent") or "").upper()
        route_score = 1.0 if expected_intent == actual_intent else 0.0

        sql_details = self._score_sql(case_id, output) if expected_intent in {"SQL", "HYBRID"} else None
        rag_details = self._score_rag(case, output) if expected_intent in {"RAG", "HYBRID"} else None
        integration = self._score_integration(output, sql_details, rag_details) if expected_intent == "HYBRID" else None

        if expected_intent == "SQL":
            score = 0.15 * route_score + 0.85 * float(sql_details["score"])
        elif expected_intent == "RAG":
            score = 0.15 * route_score + 0.85 * float(rag_details["score"])
        elif expected_intent == "HYBRID":
            score = (
                0.10 * route_score
                + 0.35 * float(sql_details["score"])
                + 0.35 * float(rag_details["score"])
                + 0.20 * float(integration["score"])
            )
        else:
            score = route_score

        score = round(score, 4)
        return {
            "automatic_score": score,
            "automatic_pass": score >= PASS_THRESHOLD,
            "automatic_pass_threshold": PASS_THRESHOLD,
            "route_score": route_score,
            "sql": sql_details,
            "rag": rag_details,
            "integration": integration,
            "metric_scope": "reference_result_and_evidence_alignment",
        }

    def _score_sql(self, case_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
        template_name = self.case_templates.get(case_id)
        if not template_name:
            return {"score": 0.0, "error": "missing_reference_sql"}
        expected_rows = self._get_reference_rows(template_name)
        actual_rows = extract_sql_rows(output)
        payload = extract_sql_payload(output)
        has_sql_branch = (
            output.get("sql_success") is not None
            or "sql" in set(output.get("branches") or [])
            or bool(payload)
        )
        if has_sql_branch:
            precision, recall, f1 = row_set_scores(actual_rows, expected_rows)
        else:
            precision, recall, f1 = 0.0, 0.0, 0.0
        sql_success = output.get("sql_success") is True or (
            has_sql_branch
            and not payload.get("error")
            and ("rows" in payload or bool(payload.get("sql_query")))
        )
        score = round(0.20 * float(sql_success) + 0.80 * f1, 4)
        return {
            "score": score,
            "template": template_name,
            "execution_success": sql_success,
            "result_precision": precision,
            "result_recall": recall,
            "result_f1": f1,
            "actual_row_count": len(actual_rows),
            "expected_row_count": len(expected_rows),
        }

    def _score_rag(self, case: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        company = expected_company(str(case.get("question") or ""))
        topic_tokens = expected_topic_tokens(str(case.get("ground_truth_answer") or ""))
        answer = str(output.get("answer") or "")
        sources, passages = extract_rag_evidence(output)
        normalized_sources = [normalize_text(source) for source in sources]
        source_match = 1.0 if company and any(company in source for source in normalized_sources) else 0.0
        rag_payload = extract_rag_payload(output)
        rag_success = output.get("rag_success") is True or (
            bool(passages or sources) and not rag_payload.get("error")
        )
        evidence_present = 1.0 if rag_success and bool(passages or sources) else 0.0
        evidence_tokens = token_set(" ".join([answer, *passages]))
        topic_recall = (
            len(topic_tokens & evidence_tokens) / len(topic_tokens)
            if topic_tokens
            else 0.0
        )
        passage_tokens = token_set(" ".join(passages))
        answer_tokens = token_set(answer) - token_set(INSUFFICIENT_EVIDENCE)
        groundedness = (
            len(answer_tokens & passage_tokens) / len(answer_tokens)
            if answer_tokens and passage_tokens
            else 0.0
        )
        score = round(
            0.25 * evidence_present
            + 0.25 * source_match
            + 0.35 * topic_recall
            + 0.15 * groundedness,
            4,
        )
        return {
            "score": score,
            "expected_company": company,
            "expected_topic_tokens": sorted(topic_tokens),
            "evidence_present": bool(evidence_present),
            "source_match": source_match,
            "topic_recall": round(topic_recall, 4),
            "extractive_groundedness": round(groundedness, 4),
            "source_count": len(sources),
        }

    @staticmethod
    def _score_integration(
        output: Dict[str, Any],
        sql_details: Optional[Dict[str, Any]],
        rag_details: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        branches = set(output.get("branches") or [])
        both_branches = {"sql", "rag"}.issubset(branches)
        sql_integrated = bool(sql_details and sql_details.get("result_f1", 0.0) > 0.0)
        rag_integrated = bool(rag_details and rag_details.get("source_match", 0.0) > 0.0)
        merged = bool(output.get("merge_used")) or "merge_template" in branches or "merge_llm" in branches
        score = round(
            (float(both_branches) + float(sql_integrated) + float(rag_integrated) + float(merged)) / 4,
            4,
        )
        return {
            "score": score,
            "both_branches": both_branches,
            "sql_result_integrated": sql_integrated,
            "document_source_integrated": rag_integrated,
            "merge_recorded": merged,
        }

    def _get_reference_rows(self, template_name: str) -> list[dict[str, Any]]:
        if template_name in self._reference_rows:
            return self._reference_rows[template_name]
        sql = self.templates[template_name]
        if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
            raise ValueError(f"Reference SQL is not read-only: {template_name}")
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = 5000")
            cursor.execute(sql)
            columns = [item.name for item in cursor.description or []]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self._reference_rows[template_name] = rows
        return rows

    def _get_connection(self):
        if self._connection is not None and not self._connection.closed:
            return self._connection
        load_dotenv(PROJECT_ROOT / ".env")
        host = os.getenv("PGHOST") or os.getenv("PG_HOST") or "localhost"
        kwargs: Dict[str, Any] = {
            "host": host,
            "port": int(os.getenv("PGPORT") or os.getenv("PG_PORT") or "5432"),
            "dbname": os.getenv("PGDATABASE") or os.getenv("PG_DB") or "northwind",
            "user": os.getenv("PGUSER") or os.getenv("PG_USER") or "postgres",
            "password": os.getenv("PGPASSWORD") or os.getenv("PG_PASSWORD") or "",
            "connect_timeout": 5,
        }
        sslmode = os.getenv("PGSSLMODE") or os.getenv("PG_SSLMODE")
        if sslmode:
            kwargs["sslmode"] = sslmode
        elif ".supabase.co" in host:
            kwargs["sslmode"] = "require"
        self._connection = psycopg2.connect(**kwargs)
        return self._connection


def extract_sql_rows(output: Dict[str, Any]) -> list[dict[str, Any]]:
    payload = extract_sql_payload(output)
    rows = payload.get("rows") or output.get("sql_result") or []
    return [row for row in rows if isinstance(row, dict)]


def extract_sql_payload(output: Dict[str, Any]) -> dict[str, Any]:
    raw = output.get("raw") or {}
    hybrid = raw.get("hybrid") or {}
    payload = raw.get("sql") or hybrid.get("sql_result") or output.get("sql_result") or {}
    return payload if isinstance(payload, dict) else {}


def extract_rag_evidence(output: Dict[str, Any]) -> tuple[list[str], list[str]]:
    payload = extract_rag_payload(output)
    sources = [str(value) for value in output.get("sources") or [] if str(value).startswith("DOC:")]
    sources.extend(str(value) for value in payload.get("citations") or [])
    passages = []
    for value in payload.get("context_passages") or []:
        passages.append(str(value.get("text") if isinstance(value, dict) else value))
    return list(dict.fromkeys(sources)), passages


def extract_rag_payload(output: Dict[str, Any]) -> dict[str, Any]:
    raw = output.get("raw") or {}
    hybrid = raw.get("hybrid") or {}
    payload = raw.get("rag") or hybrid.get("rag_result") or output.get("rag_result") or {}
    return payload if isinstance(payload, dict) else {}


def row_set_scores(
    actual_rows: Iterable[dict[str, Any]],
    expected_rows: Iterable[dict[str, Any]],
) -> tuple[float, float, float]:
    actual = Counter(canonical_row(row) for row in actual_rows)
    expected = Counter(canonical_row(row) for row in expected_rows)
    if not actual and not expected:
        return 1.0, 1.0, 1.0
    overlap = sum((actual & expected).values())
    precision = overlap / sum(actual.values()) if actual else 0.0
    recall = overlap / sum(expected.values()) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


def canonical_row(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(canonical_value(value) for value in row.values())


def canonical_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return round(float(value), 4)
    if isinstance(value, float):
        return None if math.isnan(value) else round(value, 4)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return round(float(stripped), 4)
        except ValueError:
            return normalize_text(stripped)
    return value


def expected_company(question: str) -> str:
    normalized = normalize_text(question)
    for company in ("fpt", "vinamilk", "masan"):
        if company in normalized:
            return company
    return ""


def expected_topic_tokens(ground_truth: str) -> set[str]:
    text = ground_truth
    if "RAG:" in text:
        text = text.split("RAG:", 1)[1].split(";", 1)[0]
    elif " - " in text:
        text = text.split(" - ", 1)[1]
    return token_set(text)


def token_set(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(value))
        if len(token) >= 3 and token not in STOPWORDS
    }


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", text).strip().lower()
