"""Compare a legacy table with a target table. Verdicts are PASS, FAIL, or NEED_HUMAN.

Rows are not joined on a key. The check covers schema, row count, numeric
aggregates, PSI, and KS. A key-aligned row diff is outside this version.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from migration_eval.platform_migrations.parity.stats import ks_statistic, population_stability_index

_FAIL = "fail"
_WATCH = "watch"
_INFO = "info"


@dataclass(frozen=True)
class ParityPolicy:
    row_count_rel_tol: float = 0.0
    aggregate_rel_tol: float = 0.0
    psi_watch: float = 0.10
    psi_fail: float = 0.25
    ks_watch: float = 0.10
    ks_fail: float = 0.20
    psi_bins: int = 10
    required_columns: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.row_count_rel_tol < 0 or self.aggregate_rel_tol < 0:
            raise ValueError("tolerances must be >= 0")
        if self.psi_watch < 0 or self.psi_fail < self.psi_watch:
            raise ValueError("psi_fail must be >= psi_watch >= 0")
        if self.ks_watch < 0 or self.ks_fail < self.ks_watch:
            raise ValueError("ks_fail must be >= ks_watch >= 0")
        if self.psi_bins < 1:
            raise ValueError("psi_bins must be >= 1")


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    message: str
    metric: float | None = None


@dataclass(frozen=True)
class ParityResult:
    verdict: str
    findings: tuple[Finding, ...]


def compare_tables(
    legacy: Sequence[Mapping[str, object]],
    target: Sequence[Mapping[str, object]],
    policy: ParityPolicy | None = None,
) -> ParityResult:
    active = policy or ParityPolicy()
    findings: list[Finding] = []
    legacy_cols = _columns(legacy)
    target_cols = _columns(target)
    required = set(active.required_columns or legacy_cols)
    missing = sorted(required - set(target_cols))
    extra = sorted(set(target_cols) - set(legacy_cols))
    if missing:
        findings.append(Finding("schema", _FAIL, "target is missing required columns: " + ", ".join(missing)))
    if extra:
        findings.append(Finding("schema", _WATCH, "target has extra columns: " + ", ".join(extra)))
    shared = [name for name in legacy_cols if name in set(target_cols)]
    for name in shared:
        legacy_type = _dtype([row.get(name) for row in legacy])
        target_type = _dtype([row.get(name) for row in target])
        if legacy_type == "mixed" or target_type == "mixed":
            findings.append(Finding("schema", _FAIL, f"column {name} has mixed types"))
        elif "null" in {legacy_type, target_type} and legacy_type != target_type:
            findings.append(
                Finding(
                    "schema",
                    _WATCH,
                    f"column {name} type is under-determined ({legacy_type} vs {target_type})",
                )
            )
        elif legacy_type != target_type:
            findings.append(
                Finding(
                    "schema",
                    _FAIL,
                    f"column {name} type changed from {legacy_type} to {target_type}",
                )
            )
    _compare_row_count(len(legacy), len(target), active, findings)
    if legacy and target:
        for name in shared:
            if _dtype([row.get(name) for row in legacy]) != "number":
                continue
            if _dtype([row.get(name) for row in target]) != "number":
                continue
            _compare_numeric(name, legacy, target, active, findings)
    elif not legacy and not target:
        findings.append(Finding("rows", _WATCH, "both tables are empty"))
    return ParityResult(_verdict(findings), tuple(findings))


def load_table(path: Path) -> list[dict[str, object]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "rows" in raw:
        raw = raw["rows"]
    if not isinstance(raw, list):
        raise ValueError(f"{path} does not contain a list of rows")
    rows: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{path} row {index} is not an object")
        rows.append({str(key): value for key, value in item.items()})
    return rows


def _compare_row_count(legacy_count: int, target_count: int, policy: ParityPolicy, findings: list[Finding]) -> None:
    if legacy_count == 0 or target_count == 0:
        if legacy_count != target_count:
            findings.append(
                Finding(
                    "row_count",
                    _FAIL,
                    f"row count legacy={legacy_count} target={target_count}",
                    metric=float(abs(target_count - legacy_count)),
                )
            )
        return
    relative = abs(target_count - legacy_count) / legacy_count
    if relative > policy.row_count_rel_tol:
        findings.append(
            Finding(
                "row_count",
                _FAIL,
                f"row count relative diff {relative:.6f} exceeds {policy.row_count_rel_tol}",
                metric=relative,
            )
        )


def _compare_numeric(
    name: str,
    legacy: Sequence[Mapping[str, object]],
    target: Sequence[Mapping[str, object]],
    policy: ParityPolicy,
    findings: list[Finding],
) -> None:
    left = _numbers(legacy, name)
    right = _numbers(target, name)
    if len(left) < 2 or len(right) < 2:
        findings.append(Finding("distribution", _WATCH, f"column {name} has fewer than 2 numeric values"))
        return
    for label, lhs, rhs in (
        ("sum", sum(left), sum(right)),
        ("mean", sum(left) / len(left), sum(right) / len(right)),
    ):
        relative = _relative(lhs, rhs)
        if relative > policy.aggregate_rel_tol:
            metric = None if not math.isfinite(relative) else relative
            findings.append(
                Finding(
                    "aggregate",
                    _FAIL,
                    f"column {name} {label} relative diff exceeds {policy.aggregate_rel_tol}",
                    metric=metric,
                )
            )
    psi = population_stability_index(left, right, bins=policy.psi_bins)
    ks = ks_statistic(left, right)
    _band(findings, f"psi:{name}", psi, policy.psi_watch, policy.psi_fail, "PSI")
    _band(findings, f"ks:{name}", ks, policy.ks_watch, policy.ks_fail, "KS")


def _band(findings: list[Finding], check: str, value: float, watch: float, fail: float, label: str) -> None:
    if value >= fail:
        findings.append(Finding(check, _FAIL, f"{label} {value:.6f} >= fail {fail}", metric=value))
    elif value >= watch:
        findings.append(
            Finding(
                check,
                _WATCH,
                f"{label} {value:.6f} is in the watch band [{watch}, {fail})",
                metric=value,
            )
        )
    else:
        findings.append(Finding(check, _INFO, f"{label} {value:.6f} is within the watch band", metric=value))


def _verdict(findings: Sequence[Finding]) -> str:
    if any(item.severity == _FAIL for item in findings):
        return "FAIL"
    if any(item.severity == _WATCH for item in findings):
        return "NEED_HUMAN"
    return "PASS"


def _columns(rows: Sequence[Mapping[str, object]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    return ordered


def _dtype(values: Sequence[object]) -> str:
    kinds: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            kinds.add("bool")
        elif isinstance(value, int | float):
            kinds.add("number")
        else:
            kinds.add("string")
    if not kinds:
        return "null"
    if len(kinds) > 1:
        return "mixed"
    return next(iter(kinds))


def _numbers(rows: Sequence[Mapping[str, object]], name: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(name)
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        values.append(float(value))
    return values


def _relative(left: float, right: float) -> float:
    denom = abs(left)
    if denom == 0:
        return 0.0 if right == 0 else math.inf
    return abs(right - left) / denom
