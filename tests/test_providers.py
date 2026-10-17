from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from migration_eval.compare import CONTRACT_SANITY_WARNING, IncompleteLiveRun, compare_providers
from migration_eval.golden import build_golden
from migration_eval.models import (
    Completion,
    ToolCall,
    TriageOutput,
    parse_triage,
    render_output,
    render_user_prompt,
    sim_tokens,
)
from migration_eval.paths import repo_root
from migration_eval.policy import load_policy
from migration_eval.prices import ModelPrice, PriceTable, cost_usd, load_prices
from migration_eval.providers.cassette import CassetteMiss, CassetteProvider
from migration_eval.providers.factory import build_provider
from migration_eval.providers.fake import PROFILES, FakeProvider
from migration_eval.providers.openai_compat import (
    LIVE_OUTPUT_RESERVE_TOKENS,
    LiveConfigError,
    LiveDisabled,
    LiveProvider,
    SpendCapExceeded,
    SpendTracker,
    prepare_live_compare,
    urllib_post,
)
from migration_eval.report import render_markdown
from migration_eval.retries import RetryableError
from migration_eval.spec import expected_triage


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
        system = payload["messages"][0]["content"]
        assert "true_category" not in payload["messages"][1]["content"]
        assert "order_status -> queue_orders" in system
        assert "return_request -> queue_returns" in system
        assert "exactly once" in system
        assert '"name": "route_ticket"' in system
        assert "Example:" in system
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


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("The read operation timed out"),
        ConnectionError("connection reset"),
        urllib.error.URLError("timed out"),
    ],
)
def test_urllib_post_retries_network_errors(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def failing(_request: object, timeout: float = 0) -> object:
        raise error

    monkeypatch.setattr("urllib.request.urlopen", failing)
    with pytest.raises(RetryableError, match="network error"):
        urllib_post("https://example.test", {}, b"{}", 1)


def test_live_provider_retries_timeout_then_stops(tmp_path: Path) -> None:
    calls = {"n": 0}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, object]:
        calls["n"] += 1
        if calls["n"] <= 2:
            return _chat_body()
        raise TimeoutError("The read operation timed out")

    root = repo_root()
    old, new, prices = prepare_live_compare(
        _live_env(MAX_LIVE_SPEND_USD="1"),
        cassette_dir=tmp_path,
        base_prices=load_prices(root / "config" / "prices.yaml"),
        http_post=http_post,
        sleep=lambda _delay: None,
    )
    with pytest.raises(IncompleteLiveRun, match="TimeoutError") as caught:
        compare_providers(
            old,
            new,
            build_golden()[:2],
            runs=1,
            policy=load_policy(root / "config" / "policy.yaml"),
            prices=prices,
            today="2026-10-17",
            bootstrap_rounds=5,
            stop_on_live_error=True,
        )
    assert "No further request was sent" in str(caught.value)
    assert len(caught.value.old_rows) == 1
    assert len(caught.value.new_rows) == 1
    assert calls["n"] == 5


def test_timeout_retries_stop_at_the_spend_cap() -> None:
    ticket = build_golden()[0]
    price = ModelPrice("m", "chat-completions", 0.001, 0.002, "test", "2026-10-17")
    estimate = cost_usd(price, sim_tokens(render_user_prompt(ticket)), LIVE_OUTPUT_RESERVE_TOKENS)
    calls = {"n": 0}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, object]:
        calls["n"] += 1
        raise TimeoutError("The read operation timed out")

    provider = LiveProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model="m",
        enabled=True,
        http_post=http_post,
        max_attempts=3,
        sleep=lambda _delay: None,
        spend=SpendTracker(estimate),
        price=price,
    )
    with pytest.raises(SpendCapExceeded):
        provider.complete(ticket, seed=0)
    assert calls["n"] == 1


def test_contract_failure_on_both_sides_warns_it_is_not_model_quality() -> None:
    class _ContractMiss:
        def __init__(self, name: str) -> None:
            self.name = name
            self.model = name
            self.latency_kind = "measured"

        def complete(self, ticket: object, *, seed: int) -> Completion:
            from migration_eval.models import Ticket

            assert isinstance(ticket, Ticket)
            output = expected_triage(ticket)
            invented = TriageOutput(
                category=output.category,
                priority=output.priority,
                queue="orders",
                rationale=output.rationale,
                tool_calls=(ToolCall(name="route_ticket", arguments={"queue": "orders"}),),
            )
            raw = render_output(invented)
            return Completion(
                provider=self.name,
                model=self.model,
                ticket_id=ticket.id,
                seed=seed,
                raw_text=raw,
                parsed=parse_triage(raw),
                input_tokens=1,
                output_tokens=1,
                latency_ms=1.0,
                latency_kind="measured",
                attempts=1,
            )

    root = repo_root()
    base = load_prices(root / "config" / "prices.yaml")
    models = dict(base.models)
    for name in ("live-a", "live-b"):
        models[name] = ModelPrice(name, "chat-completions", 0.001, 0.002, "test", "2026-10-17")
    report = compare_providers(
        _ContractMiss("live-a"),
        _ContractMiss("live-b"),
        build_golden(),
        runs=1,
        policy=load_policy(root / "config" / "policy.yaml"),
        prices=PriceTable(base.currency, base.note, models),
        today="2026-10-17",
        bootstrap_rounds=5,
    )
    assert report.metrics.overall.old_pass_rate == 0
    assert report.metrics.overall.new_pass_rate == 0
    assert report.metrics.harmful_old == 0
    assert report.metrics.harmful_new == 0
    assert report.metrics.contract_mismatch_old == 63
    assert report.contract_warning == CONTRACT_SANITY_WARNING
    assert CONTRACT_SANITY_WARNING in render_markdown(report)


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
