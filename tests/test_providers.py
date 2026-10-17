from __future__ import annotations

import json
from pathlib import Path

import pytest

from migration_eval.golden import build_golden
from migration_eval.models import render_user_prompt
from migration_eval.providers.cassette import CassetteMiss, CassetteProvider
from migration_eval.providers.factory import build_provider
from migration_eval.providers.fake import PROFILES, FakeProvider
from migration_eval.providers.openai_compat import (
    LiveDisabled,
    LiveProvider,
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
