"""Offline providers by default. A real platform adapter is design-only."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from migration_eval.evalkit.cassette import CassetteProvider
from migration_eval.evalkit.fake import FakeProvider
from migration_eval.platform_migrations.config import Settings


class ProviderDisabled(RuntimeError):
    """Raised instead of opening a network connection."""


def build_provider(
    settings: Settings,
    *,
    responses: Mapping[str, Mapping[str, object]] | None = None,
) -> FakeProvider | CassetteProvider:
    if settings.cassette_record:
        raise ProviderDisabled(
            "MLMIG_CASSETTE_RECORD is disabled. Author cassette JSON fixtures; "
            "this process does not contact a provider."
        )
    if settings.provider == "fake":
        return FakeProvider(responses)
    if settings.provider == "cassette":
        if not settings.cassette_path:
            raise ValueError("MLMIG_CASSETTE_PATH is required when MLMIG_PROVIDER=cassette")
        return CassetteProvider.load(Path(settings.cassette_path))
    if settings.provider == "real":
        raise ProviderDisabled(
            "MLMIG_PROVIDER=real is design-only. No socket was opened. See docs/platform-migrations/architecture.md."
        )
    raise ValueError(f"unsupported provider {settings.provider}")
