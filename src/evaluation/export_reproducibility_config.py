"""Export implementation details that reviewers commonly ask for."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.runtime.logging import write_json, write_markdown
from src.sql.text_to_sql import DISALLOWED_SQL_KEYWORDS


def implementation_config() -> dict:
    return {
        "chunk_size": 800,
        "chunk_overlap": 120,
        "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "embedding_dimension": 384,
        "embedding_multilingual": True,
        "bm25_k1": 1.5,
        "bm25_b": 0.75,
        "top_k_dense": 5,
        "top_k_sparse": 5,
        "final_top_k": 3,
        "rrf_k": 60.0,
        "vector_store": "ChromaDB cosine",
    }


def main() -> int:
    output_dir = PROJECT_ROOT / "docs" / "results"
    payload = {
        "rag": implementation_config(),
        "sql_safety": {
            "read_only_only": True,
            "disallowed_keywords": DISALLOWED_SQL_KEYWORDS,
            "database_session_readonly": True,
        },
        "hybrid": {
            "async_execution": "asyncio.gather when RuntimeConfig.parallel_enabled=True",
            "fallback_modes": ["NONE", "SQL_ONLY", "RAG_ONLY", "SQL_DOMINANT", "TEMPLATE_MERGE", "BOTH_FAILED"],
            "branch_trace_fields": [
                "rag_status",
                "sql_status",
                "fallback_mode",
                "rag_latency_ms",
                "sql_latency_ms",
                "fusion_latency_ms",
                "retrieved_chunks",
                "generated_sql",
                "sql_result",
            ],
        },
    }
    write_json(output_dir / "implementation_config.json", payload)
    lines = ["# Implementation Configuration", ""]
    for section, values in payload.items():
        lines.extend([f"## {section}", ""])
        for key, value in values.items():
            lines.append(f"- **{key}**: `{json.dumps(value, ensure_ascii=False)}`")
        lines.append("")
    write_markdown(output_dir / "implementation_config.md", "\n".join(lines))
    print(f"Exported reproducibility config to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
