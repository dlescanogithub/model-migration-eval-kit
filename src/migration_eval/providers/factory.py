"""Build a provider by name. Unknown names and a disabled live adapter fail closed."""

from __future__ import annotations

from pathlib import Path

from migration_eval.providers.base import Provider
from migration_eval.providers.cassette import CassetteProvider
from migration_eval.providers.fake import PROFILES, FakeProvider
from migration_eval.providers.openai_compat import LiveDisabled, LiveProvider, live_enabled


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
                "openai-compat is off by default. Set MIGRATION_EVAL_ENABLE_LIVE=1 to opt in. Do not set it in CI."
            )
        return LiveProvider(
            base_url=env.get("MIGRATION_EVAL_LIVE_BASE_URL", ""),
            api_key=env.get("MIGRATION_EVAL_LIVE_API_KEY", ""),
            model=env.get("MIGRATION_EVAL_LIVE_MODEL", ""),
            enabled=True,
            max_attempts=int(env.get("MIGRATION_EVAL_MAX_ATTEMPTS", "3")),
            backoff_cap_s=float(env.get("MIGRATION_EVAL_BACKOFF_CAP_S", "0.2")),
        )
    known = ", ".join(sorted([*PROFILES, "cassette", "openai-compat"]))
    raise ValueError(f"unknown provider {name!r}; known: {known}")
