"""Command line. Defaults stay offline."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from migration_eval import __version__
from migration_eval.adr import write_migration_adr
from migration_eval.canary import load_canary_criteria, simulate_canary, write_audit
from migration_eval.compare import compare_providers
from migration_eval.deprecation import check_calendar, load_calendar, render_calendar_report
from migration_eval.evalgate import evaluate_provider
from migration_eval.golden import build_golden, dump_golden, load_golden
from migration_eval.logging_setup import configure_logging, log_event
from migration_eval.models import Ticket
from migration_eval.paths import repo_root
from migration_eval.platform_migrations.cli import main as platform_main
from migration_eval.policy import load_policy
from migration_eval.prices import load_prices
from migration_eval.providers.factory import build_provider
from migration_eval.providers.openai_compat import prepare_live_compare
from migration_eval.report import render_markdown, write_report
from migration_eval.secretscan import hash_matches, scan_path
from migration_eval.trace import append_trace


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    try:
        return int(args.func(args))
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        log_event("command_error", error=str(exc))
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migration-eval",
        description=(
            "Compare two providers on a synthetic ticket-triage golden set and "
            "recommend GO, NO_GO, or NEED_HUMAN. Live providers are off by default."
        ),
    )
    parser.add_argument("--log-level", default=os.environ.get("MIGRATION_EVAL_LOG_LEVEL", "INFO"))
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare", help="compare two providers on the golden set")
    _add_common(compare)
    compare.add_argument("--old", required=True)
    compare.add_argument("--new", required=True)
    compare.add_argument("--runs", type=int, default=10)
    compare.add_argument("--out", type=Path, default=None)
    compare.add_argument("--cassette", type=Path, default=None)
    compare.add_argument("--cassette-inner", default=None)
    compare.add_argument("--record-cassette", action="store_true")
    compare.set_defaults(func=cmd_compare)

    live = sub.add_parser(
        "compare-live",
        help="compare two chat-completions models; off unless LIVE_MODE=1, never used in CI",
    )
    _add_common(live)
    live.add_argument("--runs", type=int, default=1)
    live.add_argument("--out", type=Path, default=None)
    live.add_argument("--cassette-dir", type=Path, default=None)
    live.set_defaults(func=cmd_compare_live)

    eval_cmd = sub.add_parser("eval", help="invariant gate for one offline provider")
    _add_common(eval_cmd)
    eval_cmd.add_argument("--provider", default="fake-old")
    eval_cmd.add_argument("--runs", type=int, default=5)
    eval_cmd.set_defaults(func=cmd_eval)

    regression = sub.add_parser(
        "eval-regression",
        help="forced NO_GO against fake-new-degraded; exits 1 when the gate goes red",
    )
    _add_common(regression)
    regression.add_argument("--runs", type=int, default=5)
    regression.add_argument("--out", type=Path, default=None)
    regression.set_defaults(func=cmd_eval_regression)

    canary = sub.add_parser("canary", help="simulate a stratified canary and write an audit log")
    _add_common(canary)
    canary.add_argument("--old", default="fake-old")
    canary.add_argument("--new", default="fake-new")
    canary.add_argument("--out", type=Path, default=None)
    canary.set_defaults(func=cmd_canary)

    calendar = sub.add_parser(
        "deprecation-check",
        help="warn when a calendar item is near or overdue relative to --today",
    )
    _add_common(calendar)
    calendar.set_defaults(func=cmd_deprecation)

    scan = sub.add_parser("secretscan", help="scan a tree for committed secret shapes")
    scan.add_argument("path", type=Path, nargs="?", default=None)
    scan.add_argument(
        "--check-hash",
        action="store_true",
        help="check that secretscan.py matches the sha256 recorded in docs/PROVENANCE.md",
    )
    scan.set_defaults(func=cmd_secretscan)

    golden = sub.add_parser("build-golden", help="rewrite data/golden_tickets.json from the generator")
    golden.add_argument("--out", type=Path, default=None)
    golden.set_defaults(func=cmd_build_golden)

    platform = sub.add_parser(
        "platform-migrations",
        help="inventory, waves, parity, registry rollback, and the cutover gate",
    )
    platform.add_argument("argv", nargs=argparse.REMAINDER)
    platform.set_defaults(func=cmd_platform)

    return parser


def cmd_compare(args: argparse.Namespace) -> int:
    root = repo_root()
    tickets = _tickets(root, args)
    policy = load_policy(_resolve(root, args.policy))
    prices = load_prices(_resolve(root, args.prices))
    env = dict(os.environ)
    old = build_provider(
        args.old,
        env=env,
        cassette_path=args.cassette,
        cassette_inner=args.cassette_inner,
        record_cassette=bool(args.record_cassette),
    )
    new = build_provider(args.new, env=env)
    report = compare_providers(
        old,
        new,
        tickets,
        runs=args.runs,
        policy=policy,
        prices=prices,
        today=args.today,
    )
    out = args.out if args.out is not None else root / "out" / "compare"
    write_report(report, out)
    write_migration_adr(report, out / "migration-adr.md")
    _write_trace_summary(out / "traces.jsonl", report.old_name, report.new_name, report.decision.status)
    text = render_markdown(report)
    print(text)
    log_event(
        "compare_finished",
        old=report.old_name,
        new=report.new_name,
        decision=report.decision.status,
    )
    return 0


def cmd_compare_live(args: argparse.Namespace) -> int:
    """Opt-in compare. Missing LIVE_MODE or config raises before any HTTP call."""
    root = repo_root()
    tickets = _tickets(root, args)
    policy = load_policy(_resolve(root, args.policy))
    prices = load_prices(_resolve(root, args.prices))
    cassette_dir = args.cassette_dir if args.cassette_dir is not None else root / "var" / "cassettes"
    old, new, live_prices = prepare_live_compare(
        dict(os.environ),
        cassette_dir=cassette_dir,
        base_prices=prices,
    )
    report = compare_providers(
        old,
        new,
        tickets,
        runs=args.runs,
        policy=policy,
        prices=live_prices,
        today=args.today,
    )
    out = args.out if args.out is not None else root / "out" / "compare-live"
    write_report(report, out)
    write_migration_adr(report, out / "migration-adr.md")
    _write_trace_summary(out / "traces.jsonl", report.old_name, report.new_name, report.decision.status)
    print(render_markdown(report))
    log_event(
        "compare_live_finished",
        old=report.old_name,
        new=report.new_name,
        decision=report.decision.status,
    )
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    root = repo_root()
    tickets = _tickets(root, args)
    policy = load_policy(_resolve(root, args.policy))
    prices = load_prices(_resolve(root, args.prices))
    provider = build_provider(args.provider, env=dict(os.environ))
    summary = evaluate_provider(
        provider,
        tickets,
        runs=args.runs,
        policy=policy,
        prices=prices,
    )
    print(
        f"provider={summary.provider} pass_rate={summary.pass_rate:.4f} "
        f"harmful={summary.harmful} cost_per_run={summary.cost_per_run:.6f} "
        f"p95_ms={summary.p95_latency_ms:.1f} ok={str(summary.ok).lower()}"
    )
    for failure in summary.failures:
        print(f"failure: {failure}")
    log_event("eval_finished", provider=summary.provider, ok=summary.ok)
    return 0 if summary.ok else 1


def cmd_eval_regression(args: argparse.Namespace) -> int:
    """Exit 1 when the degraded provider is NO_GO. Exit 0 only if that gate fails open."""
    root = repo_root()
    tickets = _tickets(root, args)
    policy = load_policy(_resolve(root, args.policy))
    prices = load_prices(_resolve(root, args.prices))
    env = dict(os.environ)
    old = build_provider("fake-old", env=env)
    new = build_provider("fake-new-degraded", env=env)
    report = compare_providers(
        old,
        new,
        tickets,
        runs=args.runs,
        policy=policy,
        prices=prices,
        today=args.today,
    )
    out = args.out if args.out is not None else root / "out" / "regression"
    write_report(report, out)
    print(f"decision={report.decision.status}")
    for reason in report.decision.reasons:
        print(f"reason: {reason}")
    log_event("eval_regression_finished", decision=report.decision.status)
    if report.decision.status == "NO_GO":
        return 1
    return 0


def cmd_canary(args: argparse.Namespace) -> int:
    root = repo_root()
    tickets = _tickets(root, args)
    prices = load_prices(_resolve(root, args.prices))
    criteria = load_canary_criteria(_resolve(root, args.canary))
    env = dict(os.environ)
    old = build_provider(args.old, env=env)
    new = build_provider(args.new, env=env)
    result = simulate_canary(
        old,
        new,
        tickets,
        criteria=criteria,
        prices=prices,
        today=args.today,
    )
    out = args.out if args.out is not None else root / "out" / "canary-audit.jsonl"
    write_audit(result, out)
    print(f"decision={result.decision}")
    print(f"reason: {result.reason}")
    print(f"audit: {out}")
    log_event("canary_finished", decision=result.decision, audit=str(out))
    return 0


def cmd_deprecation(args: argparse.Namespace) -> int:
    root = repo_root()
    calendar = load_calendar(_resolve(root, args.calendar))
    today = date.fromisoformat(args.today)
    statuses = check_calendar(calendar, today)
    print(render_calendar_report(calendar, statuses, today), end="")
    overdue = any(status.overdue and status.item.required for status in statuses)
    log_event("deprecation_checked", today=args.today, overdue=overdue)
    return 1 if overdue else 0


def cmd_secretscan(args: argparse.Namespace) -> int:
    root = repo_root()
    if args.check_hash:
        provenance = root / "docs" / "PROVENANCE.md"
        if hash_matches(provenance):
            print(f"secretscan: hash matches {provenance}")
            return 0
        print(f"secretscan: hash does not match {provenance}", file=sys.stderr)
        return 1
    target = args.path if args.path is not None else root
    findings = scan_path(target)
    if not findings:
        print(f"secretscan: clean ({target})")
        return 0
    for finding in findings:
        print(finding.format())
    return 1


def cmd_platform(args: argparse.Namespace) -> int:
    argv = [item for item in args.argv if item != "--"]
    return platform_main(argv)


def cmd_build_golden(args: argparse.Namespace) -> int:
    root = repo_root()
    out = args.out if args.out is not None else root / "data" / "golden_tickets.json"
    tickets = build_golden()
    dump_golden(out, tickets)
    print(f"wrote {len(tickets)} tickets to {out}")
    return 0


def _add_common(parser: argparse.ArgumentParser) -> None:
    root = _root_or_none()
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument(
        "--policy",
        type=Path,
        default=_default(root, "MIGRATION_EVAL_POLICY", "config/policy.yaml"),
    )
    parser.add_argument(
        "--prices",
        type=Path,
        default=_default(root, "MIGRATION_EVAL_PRICES", "config/prices.yaml"),
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=_default(root, "MIGRATION_EVAL_GOLDEN", "data/golden_tickets.json"),
    )
    parser.add_argument(
        "--canary",
        type=Path,
        default=_default(root, "MIGRATION_EVAL_CANARY", "config/canary.yaml"),
    )
    parser.add_argument(
        "--calendar",
        type=Path,
        default=_default(root, "MIGRATION_EVAL_CALENDAR", "config/deprecation_calendar.yaml"),
    )


def _tickets(root: Path, args: argparse.Namespace) -> list[Ticket]:
    path = _resolve(root, args.golden)
    if not path.is_file():
        return build_golden()
    return load_golden(path)


def _resolve(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def _default(root: Path | None, env_key: str, relative: str) -> Path:
    override = os.environ.get(env_key)
    if override:
        return Path(override)
    if root is None:
        return Path(relative)
    return root / relative


def _root_or_none() -> Path | None:
    try:
        return repo_root()
    except RuntimeError:
        return None


def _write_trace_summary(path: Path, old: str, new: str, decision: str) -> None:
    append_trace(
        path,
        {
            "event": "compare_summary",
            "old": old,
            "new": new,
            "decision": decision,
        },
    )
