"""Build a provider by name. Unknown names and a disabled live adapter fail closed."""

from __future__ import annotations

from pathlib import Path

from migration_eval.providers.base import Provider
from migration_eval.providers.cassette import CassetteProvider
from migration_eval.providers.fake import PROFILES, FakeProvider
from migration_eval.providers.openai_compat import LiveDisabled, build_single_live_provider, live_enabled


def build_provider(
    name: str,
    *,
    env: dict[str, str],
    cassette_path: Path | None = None,
    cassette_inner: str | None = None,
    record_cassette: bool = False,
) -> Provider:
    if name in PROFILES:
        return FakeProvider(PROFILES[name])
    if name == "cassette":
        if cassette_path is None:
            raise ValueError("cassette provider needs a path")
        inner: Provider | None = None
        if record_cassette:
            if cassette_inner is None:
                raise ValueError("recording a cassette needs --cassette-inner")
            inner = build_provider(cassette_inner, env=env)
        return CassetteProvider(cassette_path, inner=inner, record=record_cassette, name="cassette")
    if name == "openai-compat":
        if not live_enabled(env):
            raise LiveDisabled(
                "chat-completions provider is off by default. Set LIVE_MODE=1 to opt in. Do not set it in CI."
            )
        return build_single_live_provider(env)
    known = ", ".join(sorted([*PROFILES, "cassette", "openai-compat"]))
    raise ValueError(f"unknown provider {name!r}; known: {known}")
