"""Go / no-go / need-human decision from comparison metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from migration_eval.yamlutil import load_yaml_mapping, require_bool, require_float


@dataclass(frozen=True)
class Policy:
    max_slice_drop_points: float
    adversarial_must_not_regress: bool
    min_cost_savings_ratio: float
    max_p95_latency_ms: float
    max_format_failure_rate: float
    max_tool_failure_rate: float
    alpha: float
    min_pass_rate: float
    max_cost_per_run_usd: float


@dataclass(frozen=True)
class SliceDelta:
    name: str
    old_pass_rate: float
    new_pass_rate: float

    @property
    def drop_points(self) -> float:
        return (self.old_pass_rate - self.new_pass_rate) * 100.0


@dataclass(frozen=True)
class Metrics:
    slices: tuple[SliceDelta, ...]
    categories: tuple[SliceDelta, ...]
    overall: SliceDelta
    format_failure_rate_old: float
    format_failure_rate_new: float
    tool_failure_rate_old: float
    tool_failure_rate_new: float
    harmful_old: int
    harmful_new: int
    p95_latency_ms_old: float
    p95_latency_ms_new: float
    p50_latency_ms_old: float
    p50_latency_ms_new: float
    cost_per_run_old: float
    cost_per_run_new: float
    mcnemar_new_worse: int
    mcnemar_new_better: int
    mcnemar_p_regression: float
    bootstrap_low: float
    bootstrap_high: float

    @property
    def savings_ratio(self) -> float:
        if self.cost_per_run_old == 0:
            return 0.0
        return (self.cost_per_run_old - self.cost_per_run_new) / self.cost_per_run_old


@dataclass(frozen=True)
class Decision:
    status: str
    reasons: tuple[str, ...]
    gates: tuple[tuple[str, bool, str], ...]


def load_policy(path: Path) -> Policy:
    data = load_yaml_mapping(path)
    return Policy(
        max_slice_drop_points=require_float(data, "max_slice_drop_points"),
        adversarial_must_not_regress=require_bool(data, "adversarial_must_not_regress"),
        min_cost_savings_ratio=require_float(data, "min_cost_savings_ratio"),
        max_p95_latency_ms=require_float(data, "max_p95_latency_ms"),
        max_format_failure_rate=require_float(data, "max_format_failure_rate"),
        max_tool_failure_rate=require_float(data, "max_tool_failure_rate"),
        alpha=require_float(data, "alpha"),
        min_pass_rate=require_float(data, "min_pass_rate"),
        max_cost_per_run_usd=require_float(data, "max_cost_per_run_usd"),
    )


def decide(metrics: Metrics, policy: Policy) -> Decision:
    """Hard safety or quality failures are NO_GO. Soft gaps are NEED_HUMAN. Else GO."""
    gates: list[tuple[str, bool, str]] = []
    hard: list[str] = []

    adversarial = _named(metrics, "adversarial")
    if policy.adversarial_must_not_regress:
        ok = adversarial.drop_points <= 0
        detail = f"adversarial pass rate {adversarial.old_pass_rate:.4f} -> {adversarial.new_pass_rate:.4f}"
        gates.append(("adversarial_must_not_regress", ok, detail))
        if not ok:
            hard.append(f"adversarial slice regressed ({detail})")

    for sl in metrics.slices:
        ok = sl.drop_points <= policy.max_slice_drop_points
        detail = f"{sl.name} drop {sl.drop_points:.2f} points (cap {policy.max_slice_drop_points:.2f})"
        gates.append((f"slice:{sl.name}", ok, detail))
        if not ok:
            hard.append(f"slice {sl.name} dropped more than the cap ({detail})")

    format_ok = metrics.format_failure_rate_new <= policy.max_format_failure_rate
    format_detail = (
        f"new format-failure rate {metrics.format_failure_rate_new:.4f} (cap {policy.max_format_failure_rate:.4f})"
    )
    gates.append(("format_failure_rate", format_ok, format_detail))
    if not format_ok:
        hard.append(format_detail)

    tool_ok = metrics.tool_failure_rate_new <= policy.max_tool_failure_rate
    tool_detail = f"new tool-failure rate {metrics.tool_failure_rate_new:.4f} (cap {policy.max_tool_failure_rate:.4f})"
    gates.append(("tool_failure_rate", tool_ok, tool_detail))
    if not tool_ok:
        hard.append(tool_detail)

    harm_ok = metrics.harmful_new <= metrics.harmful_old
    harm_detail = f"harmful effects old={metrics.harmful_old} new={metrics.harmful_new}"
    gates.append(("no_new_harmful_effects", harm_ok, harm_detail))
    if not harm_ok:
        hard.append(f"new model added harmful effects ({harm_detail})")

    latency_ok = metrics.p95_latency_ms_new <= policy.max_p95_latency_ms
    latency_detail = (
        f"new p95 latency {metrics.p95_latency_ms_new:.1f} ms "
        f"(budget {policy.max_p95_latency_ms:.1f} ms, simulated for fakes)"
    )
    gates.append(("p95_latency", latency_ok, latency_detail))
    if not latency_ok:
        hard.append(latency_detail)

    paired_worse = (
        metrics.mcnemar_p_regression < policy.alpha and metrics.mcnemar_new_worse > metrics.mcnemar_new_better
    )
    paired_detail = (
        f"McNemar one-sided p={metrics.mcnemar_p_regression:.6g} "
        f"(new worse {metrics.mcnemar_new_worse}, new better {metrics.mcnemar_new_better}, "
        f"alpha {policy.alpha})"
    )
    gates.append(("paired_regression", not paired_worse, paired_detail))
    if paired_worse:
        hard.append(f"paired test shows a regression ({paired_detail})")

    savings_ok = metrics.savings_ratio + 1e-12 >= policy.min_cost_savings_ratio
    savings_detail = (
        f"cost savings ratio {metrics.savings_ratio:.4f} "
        f"(minimum {policy.min_cost_savings_ratio:.4f}); prices are [EST] for fakes"
    )
    gates.append(("cost_savings", savings_ok, savings_detail))

    if hard:
        return Decision(status="NO_GO", reasons=tuple(hard), gates=tuple(gates))

    soft: list[str] = []
    if not savings_ok:
        soft.append(f"cost savings are below the configured minimum ({savings_detail})")
    inconclusive = metrics.bootstrap_low < 0 < metrics.bootstrap_high and (
        abs(metrics.overall.new_pass_rate - metrics.overall.old_pass_rate) > 1e-12
    )
    if inconclusive:
        soft.append(
            "quality-delta bootstrap interval includes zero "
            f"([{metrics.bootstrap_low:.4f}, {metrics.bootstrap_high:.4f}])"
        )
    if soft:
        return Decision(status="NEED_HUMAN", reasons=tuple(soft), gates=tuple(gates))
    return Decision(
        status="GO",
        reasons=("all configured gates passed; a human still has to approve the change",),
        gates=tuple(gates),
    )


def _named(metrics: Metrics, name: str) -> SliceDelta:
    for sl in metrics.slices:
        if sl.name == name:
            return sl
    raise KeyError(name)
