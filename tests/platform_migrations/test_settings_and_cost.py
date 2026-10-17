from __future__ import annotations

import pytest

from migration_eval.platform_migrations.config import ConfigError, load_settings
from migration_eval.platform_migrations.cost import dual_run_cost


def test_settings_defaults_and_overrides() -> None:
    settings = load_settings({})
    assert settings.provider == "fake"
    assert settings.max_attempts == 3
    assert settings.cassette_record is False
    custom = load_settings(
        {
            "MLMIG_LOG_LEVEL": "debug",
            "MLMIG_PROVIDER": "cassette",
            "MLMIG_MAX_ATTEMPTS": "4",
            "MLMIG_BASE_DELAY_SECONDS": "0.2",
            "MLMIG_BACKOFF_CAP_SECONDS": "0.3",
            "MLMIG_CASSETTE_PATH": "evals/cassettes/aerolito_manifest.json",
            "MLMIG_CASSETTE_RECORD": "yes",
        }
    )
    assert custom.log_level == "DEBUG"
    assert custom.provider == "cassette"
    assert custom.max_attempts == 4
    assert custom.base_delay_seconds == 0.2
    assert custom.cassette_record is True
    assert custom.cassette_path is not None


@pytest.mark.parametrize(
    "env",
    [
        {"MLMIG_LOG_LEVEL": "LOUD"},
        {"MLMIG_PROVIDER": "prod"},
        {"MLMIG_MAX_ATTEMPTS": "0"},
        {"MLMIG_MAX_ATTEMPTS": "nope"},
        {"MLMIG_BASE_DELAY_SECONDS": "-1"},
        {"MLMIG_BACKOFF_CAP_SECONDS": "fast"},
    ],
)
def test_settings_reject_bad_env(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        load_settings(env)


def test_cost_formula_and_rejection() -> None:
    assert dual_run_cost(jobs=4, hours_per_job=0.5, rate_per_hour=10, overlap_days=14) == 280
    with pytest.raises(ValueError):
        dual_run_cost(jobs=-1, hours_per_job=1, rate_per_hour=1, overlap_days=1)
