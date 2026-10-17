"""Deprecation calendar checker. 'Today' is injected; the clock is not read."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from migration_eval.yamlutil import load_yaml_mapping, require_int, require_str


@dataclass(frozen=True)
class CalendarItem:
    id: str
    description: str
    due: date
    owner: str
    required: bool
    kind: str


@dataclass(frozen=True)
class Calendar:
    name: str
    warn_within_days: int
    items: tuple[CalendarItem, ...]


@dataclass(frozen=True)
class ItemStatus:
    item: CalendarItem
    days_until: int
    state: str

    @property
    def overdue(self) -> bool:
        return self.days_until < 0


def load_calendar(path: Path) -> Calendar:
    data = load_yaml_mapping(path)
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("calendar items must be a list")
    items: list[CalendarItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("calendar item must be a mapping")
        entry = {str(key): value for key, value in raw.items()}
        required = entry.get("required", True)
        if not isinstance(required, bool):
            raise ValueError("required must be a boolean")
        kind = entry.get("kind", "task")
        if not isinstance(kind, str):
            raise ValueError("kind must be a string")
        items.append(
            CalendarItem(
                id=require_str(entry, "id"),
                description=require_str(entry, "description"),
                due=_parse_date(require_str(entry, "due")),
                owner=require_str(entry, "owner"),
                required=required,
                kind=kind,
            )
        )
    return Calendar(
        name=require_str(data, "name"),
        warn_within_days=require_int(data, "warn_within_days"),
        items=tuple(items),
    )


def check_calendar(calendar: Calendar, today: date) -> list[ItemStatus]:
    statuses: list[ItemStatus] = []
    for item in calendar.items:
        days = (item.due - today).days
        if days < 0:
            state = "overdue"
        elif days <= calendar.warn_within_days:
            state = "due_soon"
        else:
            state = "ok"
        statuses.append(ItemStatus(item=item, days_until=days, state=state))
    return statuses


def render_calendar_report(calendar: Calendar, statuses: list[ItemStatus], today: date) -> str:
    lines = [
        f"calendar: {calendar.name}",
        f"today: {today.isoformat()} (injected)",
        f"warn_within_days: {calendar.warn_within_days}",
        "",
    ]
    for status in statuses:
        lines.append(
            f"- {status.state}: {status.item.id} due {status.item.due.isoformat()} "
            f"in {status.days_until} days owner={status.item.owner} "
            f"required={str(status.item.required).lower()} kind={status.item.kind}"
        )
    overdue = [status for status in statuses if status.overdue and status.item.required]
    if overdue:
        lines.append("")
        lines.append(f"required overdue: {len(overdue)}")
    return "\n".join(lines) + "\n"


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"due date {value!r} is not YYYY-MM-DD") from exc
