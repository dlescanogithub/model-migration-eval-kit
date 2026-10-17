"""Keep the suite offline."""

from __future__ import annotations

import os
import socket

import pytest


@pytest.fixture(autouse=True)
def _clear_platform_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("MLMIG_") or key.startswith("MIGRATION_EVAL_PLATFORM_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network is disabled in tests")

    monkeypatch.setattr(socket, "create_connection", _blocked)
