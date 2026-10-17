"""Append-only JSONL traces. One JSON object per line."""

from __future__ import annotations

import json
from pathlib import Path


def append_trace(path: Path, record: dict[str, object]) -> None:
    """Append one JSON object as a line. Creates parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str))
        handle.write("\n")


def read_traces(path: Path) -> list[dict[str, object]]:
    """Read a JSONL trace file. Missing file yields an empty list."""
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parsed: object = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        row: dict[str, object] = {}
        for key, value in parsed.items():
            row[str(key)] = value
        rows.append(row)
    return rows
