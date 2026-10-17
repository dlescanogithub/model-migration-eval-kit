"""Checklist gate. READY means the supplied evidence passed this local policy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

_STATUSES = frozenset({"pass", "fail", "pending", "waived"})
_PARITY = frozenset({"PASS", "FAIL", "NEED_HUMAN"})


@dataclass(frozen=True)
class Control:
    id: str
    title: str
    required: bool
    status: str
    approver: str | None
    evidence: str


@dataclass(frozen=True)
class GateInput:
    controls: tuple[Control, ...]
    parity_verdict: str
    parity_approved_by: str | None
    rollback_plan_present: bool
    open_high_risks: int


@dataclass(frozen=True)
class GateResult:
    verdict: str
    reasons: tuple[str, ...]


def evaluate(gate: GateInput) -> GateResult:
    blocking: list[str] = []
    needs_human: list[str] = []
    notes: list[str] = []
    if not gate.controls:
        blocking.append("no controls supplied")
    for control in gate.controls:
        if control.status not in _STATUSES:
            blocking.append(f"{control.id} has unknown status {control.status}")
            continue
        if control.status == "pass":
            continue
        if control.status == "waived":
            if not control.approver:
                blocking.append(f"{control.id} is waived without an approver")
            else:
                notes.append(f"{control.id} waived by {control.approver}")
            continue
        if control.required:
            blocking.append(f"{control.id} is {control.status}")
        else:
            notes.append(f"{control.id} is {control.status} and is not required")
    if gate.parity_verdict == "FAIL":
        blocking.append("parity verdict is FAIL")
    elif gate.parity_verdict == "NEED_HUMAN":
        if not gate.parity_approved_by:
            needs_human.append("parity verdict is NEED_HUMAN and has no approver")
        else:
            notes.append(f"parity exception approved by {gate.parity_approved_by}")
    elif gate.parity_verdict not in _PARITY:
        blocking.append(f"parity verdict {gate.parity_verdict} is not recognised")
    if gate.open_high_risks < 0:
        blocking.append("open_high_risks must be >= 0")
    elif gate.open_high_risks > 0:
        blocking.append(f"open high risks: {gate.open_high_risks}")
    if not gate.rollback_plan_present:
        blocking.append("rollback plan is missing")
    if blocking:
        return GateResult("NOT_READY", tuple(blocking + notes))
    if needs_human:
        return GateResult("NEED_HUMAN", tuple(needs_human + notes))
    if not notes:
        notes.append("all required controls satisfied")
    return GateResult("READY", tuple(notes))


def load_gate(path: Path) -> GateInput:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        raw = cast(object, json.loads(text))
    elif suffix in {".yaml", ".yml"}:
        raw = cast(object, yaml.safe_load(text))
    else:
        raise ValueError(f"unsupported gate suffix {suffix!r}")
    if not isinstance(raw, dict):
        raise ValueError("gate document must be a mapping")
    data = {str(key): value for key, value in raw.items()}
    controls_raw = data.get("controls")
    if not isinstance(controls_raw, list):
        raise ValueError("controls must be a list")
    controls: list[Control] = []
    for index, item in enumerate(controls_raw):
        if not isinstance(item, dict):
            raise ValueError(f"controls[{index}] must be a mapping")
        row = {str(key): value for key, value in item.items()}
        control_id = _text(row.get("id"), f"controls[{index}].id")
        title = _text(row.get("title"), f"controls[{index}].title")
        required = row.get("required")
        if not isinstance(required, bool):
            raise ValueError(f"{control_id} required must be a boolean")
        status = _text(row.get("status"), f"{control_id} status")
        evidence = row.get("evidence", "")
        if not isinstance(evidence, str):
            raise ValueError(f"{control_id} evidence must be a string")
        controls.append(
            Control(
                id=control_id,
                title=title,
                required=required,
                status=status,
                approver=_optional_text(row.get("approver")),
                evidence=evidence,
            )
        )
    parity = _text(data.get("parity_verdict"), "parity_verdict")
    risks = data.get("open_high_risks", 0)
    if isinstance(risks, bool) or not isinstance(risks, int):
        raise ValueError("open_high_risks must be an integer")
    rollback = data.get("rollback_plan_present")
    if not isinstance(rollback, bool):
        raise ValueError("rollback_plan_present must be a boolean")
    return GateInput(
        controls=tuple(controls),
        parity_verdict=parity,
        parity_approved_by=_optional_text(data.get("parity_approved_by")),
        rollback_plan_present=rollback,
        open_high_risks=risks,
    )


def _text(value: object, ctx: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{ctx} must be a non-empty string")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("approver must be a string or null")
    stripped = value.strip()
    return stripped or None
