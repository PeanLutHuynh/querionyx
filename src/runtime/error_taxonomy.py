"""Shared error taxonomy for evaluation and paper-facing trace exports."""

ERROR_TYPES = [
    "schema_error",
    "syntax_error",
    "unsafe_sql_blocked",
    "retrieval_insufficient",
    "misrouting",
    "router_ambiguous",
    "hybrid_fallback",
    "fusion_failure",
    "timeout",
    "unexpected_exception",
]


def classify_error(stage: str, message: str) -> str:
    text = f"{stage} {message}".lower()
    if "syntax" in text:
        return "syntax_error"
    if "column" in text or "relation" in text or "schema" in text:
        return "schema_error"
    if "disallowed sql" in text or "read-only" in text or "select" in text and "allowed" in text:
        return "unsafe_sql_blocked"
    if "retrieval" in text or "no relevant" in text or "empty answer" in text:
        return "retrieval_insufficient"
    if "ambiguous" in text:
        return "router_ambiguous"
    if "fallback" in text:
        return "hybrid_fallback"
    if "merge" in text or "fusion" in text:
        return "fusion_failure"
    if "timeout" in text:
        return "timeout"
    return "unexpected_exception"
