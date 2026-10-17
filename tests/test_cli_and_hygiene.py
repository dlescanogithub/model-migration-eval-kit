from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from migration_eval.cli import main
from migration_eval.golden import build_golden, dump_golden
from migration_eval.logging_setup import JsonFormatter, configure_logging
from migration_eval.retries import RetryableError, run_with_retries
from migration_eval.secretscan import scan_path
from migration_eval.trace import append_trace, read_traces


def test_retries_cap_and_exhaustion() -> None:
    sleeps: list[float] = []
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableError("nope")
        return "ok"

    value, attempts = run_with_retries(
        flaky,
        max_attempts=3,
        base_delay_s=0.05,
        backoff_cap_s=0.05,
        sleep=sleeps.append,
    )
    assert value == "ok"
    assert attempts == 3
    assert sleeps == [0.05, 0.05]

    def always() -> str:
        raise RetryableError("still")

    try:
        run_with_retries(
            always,
            max_attempts=2,
            base_delay_s=0.01,
            backoff_cap_s=0.2,
            sleep=lambda _s: None,
        )
    except RetryableError:
        pass
    else:
        raise AssertionError("expected RetryableError")


def test_json_log_and_trace(tmp_path: Path) -> None:
    stream_path = tmp_path / "log.txt"
    handle = stream_path.open("w", encoding="utf-8")
    logger = configure_logging("INFO", stream=handle)
    logger.info("hello", extra={"extra_fields": {"event": "ping", "api_key": "nope", "n": 1}})
    handle.close()
    line = stream_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["message"] == "hello"
    assert payload["event"] == "ping"
    assert "api_key" not in payload
    formatter = JsonFormatter()
    record = logging.LogRecord("migration_eval", logging.ERROR, __file__, 1, "x", (), None)
    assert json.loads(formatter.format(record))["level"] == "ERROR"
    trace = tmp_path / "t.jsonl"
    append_trace(trace, {"event": "compare_summary", "decision": "NO_GO"})
    rows = read_traces(trace)
    assert rows[0]["decision"] == "NO_GO"


def test_secretscan_finds_shapes_and_ignores_placeholders(tmp_path: Path) -> None:
    secret = tmp_path / "notes.txt"
    secret.write_text("token = sk-" + ("a" * 24) + "\n", encoding="utf-8")
    placeholder = tmp_path / ".env.example"
    placeholder.write_text("MIGRATION_EVAL_LIVE_API_KEY=your-api-key-here\n", encoding="utf-8")
    findings = scan_path(tmp_path)
    assert len(findings) == 1
    assert findings[0].kind == "openai_key"


def test_cli_eval_passes_and_regression_exits_red(tmp_path: Path) -> None:
    golden = tmp_path / "golden.json"
    dump_golden(golden, build_golden())
    assert (
        main(
            [
                "--log-level",
                "ERROR",
                "eval",
                "--provider",
                "fake-old",
                "--runs",
                "1",
                "--golden",
                str(golden),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "--log-level",
                "ERROR",
                "eval-regression",
                "--runs",
                "1",
                "--today",
                "2026-10-17",
                "--golden",
                str(golden),
                "--out",
                str(tmp_path / "regression"),
            ]
        )
        == 1
    )
    report = json.loads((tmp_path / "regression" / "report.json").read_text(encoding="utf-8"))
    assert report["decision"] == "NO_GO"


def test_cli_compare_canary_calendar_and_scan(tmp_path: Path) -> None:
    out = tmp_path / "compare"
    code = main(
        [
            "--log-level",
            "ERROR",
            "compare",
            "--old",
            "fake-old",
            "--new",
            "fake-new",
            "--runs",
            "1",
            "--today",
            "2026-10-17",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert (out / "report.md").is_file()
    assert (out / "migration-adr.md").is_file()
    assert "NO_GO" in (out / "report.md").read_text(encoding="utf-8")
    audit = tmp_path / "audit.jsonl"
    assert (
        main(
            [
                "--log-level",
                "ERROR",
                "canary",
                "--old",
                "fake-old",
                "--new",
                "fake-new-close",
                "--today",
                "2026-10-17",
                "--out",
                str(audit),
            ]
        )
        == 0
    )
    assert "HOLD" in audit.read_text(encoding="utf-8")
    assert main(["--log-level", "ERROR", "deprecation-check", "--today", "2026-10-17"]) == 0
    assert main(["--log-level", "ERROR", "deprecation-check", "--today", "2026-10-25"]) == 1
    assert main(["secretscan", str(tmp_path)]) == 0


def test_golden_file_matches_generator() -> None:
    from migration_eval.paths import repo_root

    path = repo_root() / "data" / "golden_tickets.json"
    assert path.is_file()
    on_disk = path.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "golden.json"
        dump_golden(target)
        assert target.read_text(encoding="utf-8") == on_disk


def test_repo_has_no_banned_client_names() -> None:
    from migration_eval.paths import repo_root

    banned = ("End" + "ava", "Rel" + "ias", "Fan " + "Universe")
    root = repo_root()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".venv", "out", "__pycache__"} for part in path.parts):
            continue
        if path.suffix in {".png", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lowered = text.lower()
        for name in banned:
            assert name.lower() not in lowered, path
