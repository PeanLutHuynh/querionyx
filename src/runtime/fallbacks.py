"""Deterministic fallback text for Querionyx V3."""

from __future__ import annotations

from typing import Any, Dict, List


INSUFFICIENT_EVIDENCE = "Tôi không có đủ thông tin đáng tin cậy để trả lời câu hỏi này."


def standardized_failure_response(question: str, reason: str) -> Dict[str, Any]:
    return {
        "answer": INSUFFICIENT_EVIDENCE,
        "sources": [],
        "intent": "UNKNOWN",
        "latency_ms": 0.0,
        "confidence": 0.0,
        "reason": reason,
        "router_type_used": "failure_fallback",
        "llm_call_count": 0,
        "branches": [],
        "fallback_used": True,
        "timeout_triggered": False,
        "sql_success": None,
        "rag_success": None,
        "merge_used": False,
        "answer_nonempty": True,
        "cache_hit": None,
        "timings": {},
        "raw": {"question": question, "error": reason},
    }


def deterministic_merge(sql_answer: str, rag_answer: str) -> str:
    parts: List[str] = []
    if sql_answer:
        parts.append(f"Structured result:\n{sql_answer}")
    if rag_answer:
        parts.append(f"Document evidence:\n{rag_answer}")
    return "\n\n".join(parts) if parts else INSUFFICIENT_EVIDENCE

