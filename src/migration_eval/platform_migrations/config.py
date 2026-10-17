"""Environment-only settings. This module does not read dotenv files."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

_PROVIDERS = frozenset({"fake", "cassette", "real"})
_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class ConfigError(ValueError):
    """Raised when an environment variable is present and unusable."""


@dataclass(frozen=True)
class Settings:
    log_level: str = "INFO"
    max_attempts: int = 3
    base_delay_seconds: float = 0.05
    backoff_cap_seconds: float = 0.5
    provider: str = "fake"
    cassette_path: str | None = None
    cassette_record: bool = False

    @property
    def retry_kwargs(self) -> dict[str, float | int]:
        return {
            "max_attempts": self.max_attempts,
            "base_delay_seconds": self.base_delay_seconds,
            "backoff_cap_seconds": self.backoff_cap_seconds,
        }


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if env is None else env
    log_level = source.get("MLMIG_LOG_LEVEL", "INFO").strip().upper()
    if log_level not in _LOG_LEVELS:
        raise ConfigError(f"MLMIG_LOG_LEVEL must be one of {sorted(_LOG_LEVELS)}")
    provider = source.get("MLMIG_PROVIDER", "fake").strip().lower()
    if provider not in _PROVIDERS:
        raise ConfigError("MLMIG_PROVIDER must be fake, cassette, or real")
    cassette = source.get("MLMIG_CASSETTE_PATH", "").strip()
    return Settings(
        log_level=log_level,
        max_attempts=_parse_int(source, "MLMIG_MAX_ATTEMPTS", 3, minimum=1),
        base_delay_seconds=_parse_float(source, "MLMIG_BASE_DELAY_SECONDS", 0.05),
        backoff_cap_seconds=_parse_float(source, "MLMIG_BACKOFF_CAP_SECONDS", 0.5),
        provider=provider,
        cassette_path=cassette or None,
        cassette_record=_parse_bool(source.get("MLMIG_CASSETTE_RECORD", "0")),
    )


def _parse_int(env: Mapping[str, str], name: str, default: int, *, minimum: int) -> int:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return value


def _parse_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if value < 0:
        raise ConfigError(f"{name} must be >= 0")
    return value


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}
