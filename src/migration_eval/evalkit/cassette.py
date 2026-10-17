"""Replay a JSON cassette. Replay does not open a socket."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast


class CassetteMismatch(RuntimeError):
    """The next call does not match the next recorded interaction."""


@dataclass(frozen=True)
class Interaction:
    operation: str
    request: dict[str, object]
    response: dict[str, object]


@dataclass(frozen=True)
class Cassette:
    name: str
    interactions: tuple[Interaction, ...]


class CassetteProvider:
    def __init__(self, cassette: Cassette) -> None:
        self.cassette = cassette
        self._pending = list(cassette.interactions)
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.network_calls = 0

    def fetch(self, operation: str, request: Mapping[str, object]) -> dict[str, object]:
        normalized = _normalize(request)
        self.calls.append((operation, normalized))
        if not self._pending:
            raise CassetteMismatch(f"cassette {self.cassette.name!r} is exhausted")
        nxt = self._pending.pop(0)
        if nxt.operation != operation or nxt.request != normalized:
            raise CassetteMismatch(f"expected {nxt.operation} {nxt.request!r}, got {operation} {normalized!r}")
        return dict(nxt.response)

    @classmethod
    def load(cls, path: Path) -> CassetteProvider:
        return cls(read_cassette(path))


def read_cassette(path: Path) -> Cassette:
    raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} cassette must be a JSON object")
    name = raw.get("name")
    interactions = raw.get("interactions")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{path} cassette name must be a string")
    if not isinstance(interactions, list):
        raise ValueError(f"{path} interactions must be a list")
    parsed: list[Interaction] = []
    for index, item in enumerate(interactions):
        if not isinstance(item, dict):
            raise ValueError(f"{path} interaction {index} must be an object")
        operation = item.get("operation")
        request = item.get("request")
        response = item.get("response")
        if not isinstance(operation, str) or not isinstance(request, dict) or not isinstance(response, dict):
            raise ValueError(f"{path} interaction {index} is missing operation, request, or response")
        parsed.append(
            Interaction(
                operation=operation,
                request=_normalize(request),
                response=_normalize(response),
            )
        )
    return Cassette(name.strip(), tuple(parsed))


def write_cassette(path: Path, cassette: Cassette) -> None:
    payload = {
        "name": cassette.name,
        "interactions": [
            {
                "operation": item.operation,
                "request": item.request,
                "response": item.response,
            }
            for item in cassette.interactions
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize(value: Mapping[str, object]) -> dict[str, object]:
    return {str(key): _freeze(item) for key, item in value.items()}


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _freeze(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_freeze(item) for item in value]
    return value
