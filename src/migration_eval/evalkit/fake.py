"""In-memory provider. network_calls stays at 0."""

from __future__ import annotations

from collections.abc import Mapping


class FakeProvider:
    def __init__(self, responses: Mapping[str, Mapping[str, object]] | None = None) -> None:
        self._responses = {
            key: {str(inner_key): value for inner_key, value in mapping.items()}
            for key, mapping in (responses or {}).items()
        }
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.network_calls = 0

    def fetch(self, operation: str, request: Mapping[str, object]) -> dict[str, object]:
        self.calls.append((operation, {str(key): value for key, value in request.items()}))
        if operation not in self._responses:
            raise KeyError(f"fake provider has no response for {operation}")
        return dict(self._responses[operation])
