"""Record/replay cassette. Replay never calls a network or an inner provider."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from migration_eval.models import Completion, Ticket, parse_triage, render_user_prompt
from migration_eval.providers.base import Provider


class CassetteMiss(Exception):
    """Replay had no row for this request. The cassette does not fall open to the network."""


class CassetteProvider:
    def __init__(
        self,
        path: Path,
        *,
        inner: Provider | None = None,
        record: bool = False,
        name: str = "cassette",
    ) -> None:
        self.path = path
        self.inner = inner
        self.record = record
        self.name = name
        self.model = name
        self.latency_kind = "simulated"
        self._rows = _load(path)

    def complete(self, ticket: Ticket, *, seed: int) -> Completion:
        key = cassette_key(self.name, ticket, seed)
        cached = self._rows.get(key)
        if cached is not None:
            return _to_completion(cached)
        if self.record and self.inner is not None:
            completion = self.inner.complete(ticket, seed=seed)
            row = _from_completion(key, completion)
            self._rows[key] = row
            _append(self.path, row)
            return completion
        raise CassetteMiss(
            f"no cassette row for {ticket.id} seed {seed}; recording is off and there is no network fallback"
        )


def cassette_key(provider_name: str, ticket: Ticket, seed: int) -> str:
    payload = json.dumps(
        {
            "provider": provider_name,
            "seed": seed,
            "ticket_id": ticket.id,
            "prompt": render_user_prompt(ticket),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load(path: Path) -> dict[str, dict[str, object]]:
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parsed: object = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"{path} has a non-object cassette row")
        key = parsed.get("key")
        if not isinstance(key, str):
            raise ValueError("cassette row missing key")
        row: dict[str, object] = {}
        for item_key, value in parsed.items():
            row[str(item_key)] = value
        rows[key] = row
    return rows


def _append(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _from_completion(key: str, completion: Completion) -> dict[str, object]:
    return {
        "key": key,
        "provider": completion.provider,
        "model": completion.model,
        "ticket_id": completion.ticket_id,
        "seed": completion.seed,
        "raw_text": completion.raw_text,
        "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens,
        "latency_ms": completion.latency_ms,
        "latency_kind": completion.latency_kind,
        "attempts": completion.attempts,
    }


def _to_completion(row: dict[str, object]) -> Completion:
    raw = row["raw_text"]
    if not isinstance(raw, str):
        raise ValueError("cassette raw_text must be a string")
    return Completion(
        provider=_as_str(row, "provider"),
        model=_as_str(row, "model"),
        ticket_id=_as_str(row, "ticket_id"),
        seed=_as_int(row, "seed"),
        raw_text=raw,
        parsed=parse_triage(raw),
        input_tokens=_as_int(row, "input_tokens"),
        output_tokens=_as_int(row, "output_tokens"),
        latency_ms=_as_float(row, "latency_ms"),
        latency_kind=_as_str(row, "latency_kind"),
        attempts=_as_int(row, "attempts"),
    )


def _as_str(row: dict[str, object], key: str) -> str:
    value = row[key]
    if not isinstance(value, str):
        raise ValueError(f"cassette {key} must be a string")
    return value


def _as_int(row: dict[str, object], key: str) -> int:
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"cassette {key} must be an integer")
    return value


def _as_float(row: dict[str, object], key: str) -> float:
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"cassette {key} must be a number")
    return float(value)
