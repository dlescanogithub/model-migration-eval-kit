"""Shared records for tickets, model outputs, and completions."""

from __future__ import annotations

import json
from dataclasses import dataclass

SLICES: tuple[str, ...] = ("happy", "edge", "adversarial")
CATEGORIES: tuple[str, ...] = (
    "order_status",
    "return_request",
    "product_question",
    "shipping",
    "payment",
    "complaint",
    "other",
)
PRIORITIES: tuple[str, ...] = ("low", "medium", "high")
QUEUE_FOR_CATEGORY: dict[str, str] = {
    "order_status": "queue_orders",
    "return_request": "queue_returns",
    "product_question": "queue_catalog",
    "shipping": "queue_logistics",
    "payment": "queue_billing",
    "complaint": "queue_care",
    "other": "queue_general",
}
ALLOWED_TOOLS: frozenset[str] = frozenset({"route_ticket"})
SAFE_RATIONALE = "Clasificado segun el contenido del pedido. No se repiten datos de contacto."


@dataclass(frozen=True)
class Ticket:
    """One synthetic Casa Brisa support ticket.

    true_category and the severity flags are the labeling spec. They are not
    part of the prompt sent to a live provider. variant is simulator metadata
    (which scripted fault a fake provider may apply); it is also not prompted.
    """

    id: str
    slice: str
    true_category: str
    subject: str
    body: str
    urgent: bool = False
    payment_severity: str = "none"
    shipping_severity: str = "none"
    pii_token: str | None = None
    injection: str | None = None
    variant: str = "standard"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "slice": self.slice,
            "true_category": self.true_category,
            "subject": self.subject,
            "body": self.body,
            "urgent": self.urgent,
            "payment_severity": self.payment_severity,
            "shipping_severity": self.shipping_severity,
            "pii_token": self.pii_token,
            "injection": self.injection,
            "variant": self.variant,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Ticket:
        return cls(
            id=_req_str(data, "id"),
            slice=_req_str(data, "slice"),
            true_category=_req_str(data, "true_category"),
            subject=_req_str(data, "subject"),
            body=_req_str(data, "body"),
            urgent=_req_bool(data, "urgent"),
            payment_severity=_req_str(data, "payment_severity"),
            shipping_severity=_req_str(data, "shipping_severity"),
            pii_token=_opt_str(data, "pii_token"),
            injection=_opt_str(data, "injection"),
            variant=_req_str(data, "variant"),
        )


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, str]


@dataclass(frozen=True)
class TriageOutput:
    category: str
    priority: str
    queue: str
    rationale: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class Completion:
    provider: str
    model: str
    ticket_id: str
    seed: int
    raw_text: str
    parsed: TriageOutput | None
    input_tokens: int
    output_tokens: int
    latency_ms: float
    latency_kind: str
    attempts: int


def render_user_prompt(ticket: Ticket) -> str:
    """The only text a live provider is allowed to see."""
    return f"subject: {ticket.subject}\nbody: {ticket.body}\n"


def render_output(output: TriageOutput, *, schema_drift: bool = False) -> str:
    payload: dict[str, object] = {
        "category": output.category,
        "priority": output.priority,
        "queue": output.queue,
        "rationale": output.rationale,
        "tool_calls": [{"name": call.name, "arguments": call.arguments} for call in output.tool_calls],
    }
    if schema_drift:
        payload["schema_version"] = "2024-legacy"
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def parse_triage(raw: str) -> TriageOutput | None:
    """Parse a model payload. Unknown keys are ignored. Invalid shapes return None."""
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    category = data.get("category")
    priority = data.get("priority")
    queue = data.get("queue")
    rationale = data.get("rationale")
    if not all(isinstance(item, str) and item for item in (category, priority, queue, rationale)):
        return None
    if priority not in PRIORITIES:
        return None
    tool_calls = _parse_tools(data.get("tool_calls"))
    if tool_calls is None:
        return None
    return TriageOutput(
        category=str(category),
        priority=str(priority),
        queue=str(queue),
        rationale=str(rationale),
        tool_calls=tool_calls,
    )


def sim_tokens(text: str) -> int:
    """Simulated token count: about four characters per token, at least one."""
    return max(1, (len(text) + 3) // 4)


def _parse_tools(raw: object) -> tuple[ToolCall, ...] | None:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        return None
    calls: list[ToolCall] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        arguments = item.get("arguments", {})
        if not isinstance(name, str) or not name:
            return None
        if not isinstance(arguments, dict):
            return None
        cleaned: dict[str, str] = {}
        for key, value in arguments.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return None
            cleaned[key] = value
        calls.append(ToolCall(name=name, arguments=cleaned))
    return tuple(calls)


def _req_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _req_bool(data: dict[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _opt_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value
