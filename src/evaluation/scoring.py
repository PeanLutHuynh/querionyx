"""Deterministic scoring for Querionyx V3 benchmark runs."""

from __future__ import annotations

from typing import Any, Dict, Iterable


def expected_intent(case: Dict[str, Any]) -> str:
    return str(case.get("expected_intent") or case.get("ground_truth_intent") or "").upper()


def query_id(case: Dict[str, Any], index: int) -> str:
    return str(case.get("query_id") or case.get("id") or f"q_{index:04d}")


def score_case(case: Dict[str, Any], output: Dict[str, Any], max_latency_ms: int) -> Dict[str, Any]:
    expected = expected_intent(case)
    actual = str(output.get("intent") or "").upper()
    answer = str(output.get("answer") or "").strip()
    keywords = case.get("expected_keywords") or []
    keyword_pass = _contains_keywords(answer, keywords)
    answer_nonempty = bool(answer)
    latency_ok = float(output.get("latency_ms") or 999999999) <= max_latency_ms
    intent_ok = not expected or expected == actual or _allowed_intent_match(expected, actual)

    sql_required = bool(case.get("requires_sql")) or expected == "SQL"
    rag_required = bool(case.get("requires_rag")) or expected == "RAG"
    hybrid_required = expected == "HYBRID"

    sql_ok = output.get("sql_success")
    rag_ok = output.get("rag_success")
    sql_pass = (not sql_required) or sql_ok is True
    rag_pass = (not rag_required) or rag_ok is True
    hybrid_pass = (not hybrid_required) or bool({"sql", "rag"} & set(output.get("branches") or []))

    passed = answer_nonempty and latency_ok and intent_ok and keyword_pass and sql_pass and rag_pass and hybrid_pass
    return {
        "passed": passed,
        "intent_ok": intent_ok,
        "answer_nonempty": answer_nonempty,
        "latency_ok": latency_ok,
        "keyword_pass": keyword_pass,
        "sql_pass": sql_pass,
        "rag_pass": rag_pass,
        "hybrid_pass": hybrid_pass,
    }


def _contains_keywords(answer: str, keywords: Iterable[str]) -> bool:
    items = [str(k).lower() for k in keywords if str(k).strip()]
    if not items:
        return True
    answer_lower = answer.lower()
    return any(item in answer_lower for item in items)


def _allowed_intent_match(expected: str, actual: str) -> bool:
    if expected == "HYBRID" and actual in {"SQL", "RAG"}:
        return False
    return False

