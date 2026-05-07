"""Append-safe structured logging for evaluation and deployment smoke runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Any]) -> None:
    """Write CSV file from list of dicts or list of lists."""
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not materialized:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Check if rows are dicts or lists
        if isinstance(materialized[0], dict):
            fieldnames = sorted({key for row in materialized for key in row.keys()})
            writer.writerow(fieldnames)
            for row in materialized:
                writer.writerow([row.get(fn, "") for fn in fieldnames])
        else:
            # Assume list of lists
            for row in materialized:
                writer.writerow(row)


def write_markdown(path: Path, content: str) -> None:
    """Write markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

