from __future__ import annotations

import json
from pathlib import Path

import pytest

from migration_eval.compare import compare_providers
from migration_eval.golden import build_golden
from migration_eval.models import render_user_prompt
from migration_eval.paths import repo_root
from migration_eval.policy import load_policy
from migration_eval.prices import load_prices
from migration_eval.providers.cassette import CassetteMiss, CassetteProvider
from migration_eval.providers.factory import build_provider
from migration_eval.providers.fake import PROFILES, FakeProvider
from migration_eval.providers.openai_compat import (
    LiveConfigError,
    LiveDisabled,
    LiveProvider,
    SpendCapExceeded,
    prepare_live_compare,
    urllib_post,
)
from migration_eval.retries import RetryableError


def test_fake_profiles_are_seed_stable_and_offline() -> None:
    ticket = build_golden()[10]
    provider = FakeProvider(PROFILES["fake-old"])
    first = provider.complete(ticket, seed=1)
    second = provider.complete(ticket, seed=1)
    assert first.raw_text == second.raw_text
    assert first.latency_kind == "simulated"
    assert "true_category" not in render_user_prompt(ticket)
    assert "edge_hard" not in render_user_prompt(ticket)
    jitter = provider.complete(ticket, seed=2)
    assert jitter.raw_text == first.raw_text
    assert jitter.latency_ms != first.latency_ms or PROFILES["fake-old"].latency_spread_ms == 0


def test_factory_rejects_live_by_default_and_unknown_names() -> None:
    with pytest.raises(LiveDisabled):
        build_provider("openai-compat", env={})
    with pytest.raises(ValueError):
        build_provider("nope", env={})
    assert build_provider("fake-old", env={}).name == "fake-old"


def test_cassette_replay_miss_and_record(tmp_path: Path) -> None:
    path = tmp_path / "tape.jsonl"
    ticket = build_golden()[0]
    inner = FakeProvider(PROFILES["fake-old"])
    recorder = CassetteProvider(path, inner=inner, record=True, name="cassette")
    recorded = recorder.complete(ticket, seed=0)
    player = CassetteProvider(path, inner=None, record=False, name="cassette")
    replayed = player.complete(ticket, seed=0)
    assert replayed.raw_text == recorded.raw_text
    with pytest.raises(CassetteMiss):
        player.complete(ticket, seed=1)
    closed = CassetteProvider(path, inner=inner, record=False, name="cassette")
    with pytest.raises(CassetteMiss):
        closed.complete(build_golden()[1], seed=0)


def test_live_provider_uses_injected_http_and_retries() -> None:
    calls = {"n": 0}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, object]:
        calls["n"] += 1
        assert url.endswith("/chat/completions")
        assert headers["Authorization"].startswith("Bearer ")
        assert timeout > 0
        payload = json.loads(body.decode("utf-8"))
        assert "true_category" not in payload["messages"][1]["content"]
        if calls["n"] == 1:
            raise RetryableError("http 503")
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "category": "other",
                                "priority": "low",
                                "queue": "queue_general",
                                "rationale": "ok",
                                "tool_calls": [
                                    {
                                        "name": "route_ticket",
                                        "arguments": {"queue": "queue_general"},
                                    }
                                ],
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        }

    with pytest.raises(LiveDisabled):
        LiveProvider(base_url="https://example.test", api_key="k", model="m", enabled=False)
    provider = LiveProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model="m",
        enabled=True,
        http_post=http_post,
        max_attempts=2,
        sleep=lambda _delay: None,
    )
    ticket = build_golden()[0]
    completion = provider.complete(ticket, seed=0)
    assert completion.attempts == 2
    assert completion.parsed is not None
    assert completion.input_tokens == 12
    assert calls["n"] == 2


def test_urllib_post_retries_http_and_reads_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(_request: object, timeout: float = 0) -> _Response:
        assert timeout == 5
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    payload = urllib_post("https://example.test/v1/chat/completions", {}, b"{}", 5)
    assert payload == {"ok": True}

    import urllib.error

    def failing(_request: object, timeout: float = 0) -> _Response:
        raise urllib.error.HTTPError("https://example.test", 503, "nope", hdrs=None, fp=None)

    monkeypatch.setattr("urllib.request.urlopen", failing)
    with pytest.raises(RetryableError):
        urllib_post("https://example.test", {}, b"{}", 1)


def _live_env(**overrides: str) -> dict[str, str]:
    env = {
        "LIVE_MODE": "1",
        "LLM_BASE_URL": "https://host.example/v1",
        "LLM_API_KEY": "local-test-key",
        "LLM_MODEL": "model-a",
        "LLM_MODEL_OLD": "model-a",
        "LLM_MODEL_NEW": "model-b",
        "MAX_LIVE_SPEND_USD": "1",
        "LLM_USD_PER_M_INPUT": "1",
        "LLM_USD_PER_M_OUTPUT": "2",
        "LLM_PRICE_DATE": "2026-10-17",
    }
    env.update(overrides)
    return env


def _chat_body() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "category": "other",
                            "priority": "low",
                            "queue": "queue_general",
                            "rationale": "ok",
                            "tool_calls": [{"name": "route_ticket", "arguments": {"queue": "queue_general"}}],
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 12},
    }


def test_factory_live_mode_missing_config_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("urlopen")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(LiveConfigError):
        build_provider("openai-compat", env={"LIVE_MODE": "1"})


def test_spend_cap_blocks_before_http(tmp_path: Path) -> None:
    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, object]:
        raise AssertionError(url)

    root = repo_root()
    old, new, prices = prepare_live_compare(
        _live_env(MAX_LIVE_SPEND_USD="0"),
        cassette_dir=tmp_path,
        base_prices=load_prices(root / "config" / "prices.yaml"),
        http_post=http_post,
        sleep=lambda _delay: None,
    )
    with pytest.raises(SpendCapExceeded):
        compare_providers(
            old,
            new,
            build_golden()[:1],
            runs=1,
            policy=load_policy(root / "config" / "policy.yaml"),
            prices=prices,
            today="2026-10-17",
            bootstrap_rounds=5,
        )


def test_live_compare_writes_cassettes_and_replays(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, object]:
        calls["n"] += 1
        assert url.endswith("/chat/completions")
        assert timeout > 0
        assert "local-test-key" not in url
        return _chat_body()

    def boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("urlopen")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    root = repo_root()
    base = load_prices(root / "config" / "prices.yaml")
    policy = load_policy(root / "config" / "policy.yaml")
    tickets = build_golden()
    old, new, prices = prepare_live_compare(
        _live_env(),
        cassette_dir=tmp_path,
        base_prices=base,
        http_post=http_post,
        sleep=lambda _delay: None,
    )
    compare_providers(
        old,
        new,
        tickets,
        runs=1,
        policy=policy,
        prices=prices,
        today="2026-10-17",
        bootstrap_rounds=5,
    )
    assert calls["n"] == len(tickets) * 2
    assert list(tmp_path.glob("*.jsonl"))
    assert "not stored in the repo" in prices.note

    def replay_http(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, object]:
        raise AssertionError("replay must not call http")

    old_again, new_again, prices_again = prepare_live_compare(
        _live_env(),
        cassette_dir=tmp_path,
        base_prices=base,
        http_post=replay_http,
        sleep=lambda _delay: None,
    )
    compare_providers(
        old_again,
        new_again,
        tickets,
        runs=1,
        policy=policy,
        prices=prices_again,
        today="2026-10-17",
        bootstrap_rounds=5,
    )
