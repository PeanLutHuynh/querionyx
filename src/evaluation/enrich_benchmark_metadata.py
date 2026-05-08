"""Add reproducibility metadata to benchmark queries.

This keeps the original question text intact and adds reviewer-facing fields such
as ambiguity, aggregation requirement, and document-reasoning requirement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


SQL_TERMS = {"bao nhiêu", "tổng", "trung bình", "top", "doanh thu", "count", "sum", "average", "total", "rank"}
DOC_TERMS = {"báo cáo", "chiến lược", "chính sách", "rủi ro", "kế hoạch", "mục tiêu", "strategy", "policy", "risk"}
AGG_TERMS = {"bao nhiêu", "tổng", "trung bình", "count", "sum", "average", "total"}


def enrich(path: Path, output: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    queries = payload.get("queries", payload)
    for query in queries:
        q = str(query.get("question", "")).lower()
        has_sql = any(term in q for term in SQL_TERMS)
        has_doc = any(term in q for term in DOC_TERMS)
        query.setdefault("requires_aggregation", any(term in q for term in AGG_TERMS))
        query.setdefault("requires_document_reasoning", has_doc)
        query.setdefault("ambiguity", "high" if has_sql and has_doc else "medium" if " và " in q or " and " in q else "low")
        query.setdefault("noise_type", "mixed_source" if has_sql and has_doc else "clean")
        query.setdefault("metadata_version", "v2_observability")
    if isinstance(payload, dict) and "queries" in payload:
        payload.setdefault("metadata", {})
        payload["metadata"]["metadata_version"] = "v2_observability"
        payload["metadata"]["fields_added"] = [
            "requires_aggregation",
            "requires_document_reasoning",
            "ambiguity",
            "noise_type",
            "metadata_version",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich benchmark metadata.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    enrich(args.dataset, args.output)
    print(f"Wrote enriched benchmark to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
