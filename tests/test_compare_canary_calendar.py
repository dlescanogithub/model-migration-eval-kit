from __future__ import annotations

from datetime import date
from pathlib import Path

from migration_eval.canary import load_canary_criteria, simulate_canary
from migration_eval.compare import compare_providers
from migration_eval.deprecation import check_calendar, load_calendar
from migration_eval.evalgate import evaluate_provider
from migration_eval.golden import build_golden
from migration_eval.paths import repo_root
from migration_eval.policy import load_policy
from migration_eval.prices import cost_usd, load_prices
from migration_eval.providers.fake import PROFILES, FakeProvider


def _bundle(name: str, runs: int = 2):
    root = repo_root()
    tickets = build_golden()
    policy = load_policy(root / "config" / "policy.yaml")
    prices = load_prices(root / "config" / "prices.yaml")
    report = compare_providers(
        FakeProvider(PROFILES["fake-old"]),
        FakeProvider(PROFILES[name]),
        tickets,
        runs=runs,
        policy=policy,
        prices=prices,
        today="2026-10-17",
        bootstrap_rounds=40,
    )
    return report


def test_named_profiles_decide_as_designed() -> None:
    assert _bundle("fake-new").decision.status == "NO_GO"
    assert _bundle("fake-new-degraded").decision.status == "NO_GO"
    assert _bundle("fake-new-close").decision.status == "GO"
    assert _bundle("fake-new-flat").decision.status == "NEED_HUMAN"
    edge = next(item for item in _bundle("fake-new").metrics.slices if item.name == "edge")
    assert edge.drop_points > 5
    degraded = _bundle("fake-new-degraded", runs=1)
    assert degraded.metrics.harmful_new > 0


def test_seed_repeats_do_not_change_ticket_inference() -> None:
    one = _bundle("fake-new", runs=1)
    ten = _bundle("fake-new", runs=10)
    assert one.metrics.analysis_n == 63
    assert ten.metrics.analysis_n == 63
    assert one.metrics.mcnemar_new_worse == 8
    assert one.metrics.mcnemar_new_better == 0
    assert one.metrics.mcnemar_p_regression == ten.metrics.mcnemar_p_regression
    assert one.metrics.mcnemar_new_worse == ten.metrics.mcnemar_new_worse
    assert one.metrics.mcnemar_new_better == ten.metrics.mcnemar_new_better
    assert one.metrics.bootstrap_low == ten.metrics.bootstrap_low
    assert one.metrics.bootstrap_high == ten.metrics.bootstrap_high
    assert one.metrics.harmful_new == ten.metrics.harmful_new
    for left, right in zip(one.metrics.slices, ten.metrics.slices, strict=True):
        assert left.n == right.n
        assert left.n > 0
        assert left.old_pass_rate == right.old_pass_rate
        assert left.new_pass_rate == right.new_pass_rate
        assert left.bootstrap_low == right.bootstrap_low
        assert left.bootstrap_high == right.bootstrap_high
    degraded = _bundle("fake-new-degraded", runs=10)
    once = _bundle("fake-new-degraded", runs=1)
    assert degraded.metrics.harmful_new == once.metrics.harmful_new
    assert degraded.metrics.mcnemar_p_regression == once.metrics.mcnemar_p_regression
    assert degraded.metrics.analysis_n == 63


def test_reference_provider_passes_the_eval_gate() -> None:
    root = repo_root()
    summary = evaluate_provider(
        FakeProvider(PROFILES["fake-old"]),
        build_golden(),
        runs=1,
        policy=load_policy(root / "config" / "policy.yaml"),
        prices=load_prices(root / "config" / "prices.yaml"),
    )
    assert summary.ok
    assert summary.harmful == 0
    assert summary.pass_rate == 1.0


def test_canary_rolls_back_a_regression_and_holds_a_close_model() -> None:
    root = repo_root()
    tickets = build_golden()
    prices = load_prices(root / "config" / "prices.yaml")
    criteria = load_canary_criteria(root / "config" / "canary.yaml")
    bad = simulate_canary(
        FakeProvider(PROFILES["fake-old"]),
        FakeProvider(PROFILES["fake-new"]),
        tickets,
        criteria=criteria,
        prices=prices,
        today="2026-10-17",
    )
    good = simulate_canary(
        FakeProvider(PROFILES["fake-old"]),
        FakeProvider(PROFILES["fake-new-close"]),
        tickets,
        criteria=criteria,
        prices=prices,
        today="2026-10-17",
    )
    harmful = simulate_canary(
        FakeProvider(PROFILES["fake-old"]),
        FakeProvider(PROFILES["fake-new-degraded"]),
        tickets,
        criteria=criteria,
        prices=prices,
        today="2026-10-17",
    )
    assert bad.decision == "ROLLBACK"
    assert good.decision == "HOLD"
    assert harmful.decision == "ROLLBACK"
    assert harmful.canary_harmful > 0
    assert bad.events[-1]["event"] == "decision"


def test_calendar_warns_and_flags_overdue() -> None:
    calendar = load_calendar(repo_root() / "config" / "deprecation_calendar.yaml")
    soon = check_calendar(calendar, date(2026, 10, 17))
    assert any(item.state == "due_soon" and item.item.id == "shadow-review" for item in soon)
    assert not any(item.overdue for item in soon)
    later = check_calendar(calendar, date(2026, 10, 25))
    assert any(item.overdue and item.item.id == "shadow-review" for item in later)


def test_price_math_is_linear() -> None:
    prices = load_prices(repo_root() / "config" / "prices.yaml")
    price = prices.for_model("fake-new")
    assert price.source.startswith("[EST]")
    assert cost_usd(price, 1000, 0) == price.usd_per_1k_input
    assert cost_usd(price, 0, 2000) == price.usd_per_1k_output * 2


def test_repo_root_finds_this_checkout() -> None:
    root = repo_root()
    assert (root / "pyproject.toml").is_file()
    assert Path(root / "config" / "policy.yaml").is_file()
