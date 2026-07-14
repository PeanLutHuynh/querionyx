"""Read and write the versioned annual-report chunk corpus.

The repository stores chunks as compressed JSON instead of pickle so a clone is
smaller and loading repository data never executes Python object constructors.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.json.gz"
REQUIRED_FIELDS = {"source", "page", "text"}


def load_chunks(path: Path = CHUNKS_FILE) -> list[dict[str, Any]]:
    """Load and minimally validate a compressed JSON chunk list."""
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError(f"Chunk store must contain a JSON list: {path}")

    chunks: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Chunk {index} is not a JSON object")
        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            raise ValueError(f"Chunk {index} is missing fields: {', '.join(sorted(missing))}")
        chunks.append(item)
    return chunks


def save_chunks(chunks: Iterable[dict[str, Any]], path: Path = CHUNKS_FILE) -> int:
    """Validate and atomically save chunks using deterministic gzip output."""
    normalized = list(chunks)
    for index, item in enumerate(normalized):
        if not isinstance(item, dict):
            raise ValueError(f"Chunk {index} is not a mapping")
        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            raise ValueError(f"Chunk {index} is missing fields: {', '.join(sorted(missing))}")

    raw = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_bytes(compressed)
    temporary.replace(path)
    return len(normalized)
