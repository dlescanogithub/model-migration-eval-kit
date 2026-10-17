"""Deterministic simulators. They are not language models.

Quality faults are a function of (profile, ticket). Latency jitter is a
function of (profile, ticket, seed) and is labelled simulated. A profile may
read ticket.variant; that field is never placed in the user prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from migration_eval.models import (
    SAFE_RATIONALE,
    Completion,
    Ticket,
    parse_triage,
    render_output,
    render_user_prompt,
    sim_tokens,
)
from migration_eval.spec import correct_output, injection_obeyed_output, wrong_category_output


@dataclass(frozen=True)
class FakeProfile:
    name: str
    price_key: str
    latency_base_ms: float
    latency_spread_ms: int
    edge_hard_fail: bool
    format_break: bool
    obey_injection: bool
    schema_drift: bool


PROFILES: dict[str, FakeProfile] = {
    "fake-old": FakeProfile(
        name="fake-old",
        price_key="fake-old",
        latency_base_ms=420.0,
        latency_spread_ms=40,
        edge_hard_fail=False,
        format_break=False,
        obey_injection=False,
        schema_drift=False,
    ),
    "fake-new": FakeProfile(
        name="fake-new",
        price_key="fake-new",
        latency_base_ms=180.0,
        latency_spread_ms=30,
        edge_hard_fail=True,
        format_break=True,
        obey_injection=False,
        schema_drift=True,
    ),
    "fake-new-degraded": FakeProfile(
        name="fake-new-degraded",
        price_key="fake-new-degraded",
        latency_base_ms=180.0,
        latency_spread_ms=30,
        edge_hard_fail=True,
        format_break=False,
        obey_injection=True,
        schema_drift=False,
    ),
    "fake-new-close": FakeProfile(
        name="fake-new-close",
        price_key="fake-new-close",
        latency_base_ms=180.0,
        latency_spread_ms=30,
        edge_hard_fail=False,
        format_break=False,
        obey_injection=False,
        schema_drift=False,
    ),
    "fake-new-flat": FakeProfile(
        name="fake-new-flat",
        price_key="fake-new-flat",
        latency_base_ms=200.0,
        latency_spread_ms=20,
        edge_hard_fail=False,
        format_break=False,
        obey_injection=False,
        schema_drift=False,
    ),
}


class FakeProvider:
    """Scripted provider. complete() does not touch the network."""

    def __init__(self, profile: FakeProfile) -> None:
        self.profile = profile
        self.name = profile.name
        self.model = profile.name
        self.latency_kind = "simulated"

    def complete(self, ticket: Ticket, *, seed: int) -> Completion:
        prompt = render_user_prompt(ticket)
        raw, parsed_hint = self._payload(ticket)
        parsed = parse_triage(raw)
        if parsed_hint is None:
            parsed = None
        return Completion(
            provider=self.name,
            model=self.model,
            ticket_id=ticket.id,
            seed=seed,
            raw_text=raw,
            parsed=parsed,
            input_tokens=sim_tokens(prompt),
            output_tokens=sim_tokens(raw),
            latency_ms=_latency(self.profile, ticket.id, seed),
            latency_kind=self.latency_kind,
            attempts=1,
        )

    def _payload(self, ticket: Ticket) -> tuple[str, object]:
        profile = self.profile
        if profile.format_break and ticket.variant == "format_break":
            return "NOT_JSON", None
        if profile.obey_injection and ticket.injection:
            output = injection_obeyed_output(ticket)
            return render_output(output), output
        if profile.edge_hard_fail and ticket.variant == "edge_hard":
            output = wrong_category_output(ticket)
            return render_output(output), output
        output = correct_output(ticket)
        if output.rationale != SAFE_RATIONALE:
            raise RuntimeError("correct output leaked an unexpected rationale")
        return render_output(output, schema_drift=profile.schema_drift), output


def _latency(profile: FakeProfile, ticket_id: str, seed: int) -> float:
    spread = profile.latency_spread_ms
    wobble = (sum(ord(char) for char in ticket_id) + seed * 17) % (spread + 1)
    return profile.latency_base_ms + float(wobble)
