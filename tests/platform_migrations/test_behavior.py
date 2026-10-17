import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from tests.platform_migrations.helpers import dataset, manifest

from migration_eval.evalkit.cassette import (
    Cassette,
    CassetteMismatch,
    CassetteProvider,
    Interaction,
    write_cassette,
)
from migration_eval.evalkit.fake import FakeProvider
from migration_eval.evalkit.runner import run_invariants
from migration_eval.platform_migrations.adapters.ports import ProviderDisabled, build_provider
from migration_eval.platform_migrations.cli import main
from migration_eval.platform_migrations.config import Settings
from migration_eval.platform_migrations.cutover.gate import Control, GateInput, evaluate
from migration_eval.platform_migrations.inventory.scanner import scan_path
from migration_eval.platform_migrations.paths import data_root

ROOT = data_root()


def test_eval_demo_and_commands(tmp_path: Path) -> None:
    assert main(["eval", "--root", str(ROOT)]) == 0
    code = main(["eval-regression", "--root", str(ROOT)])
    assert code == 1
    out = tmp_path / "demo"
    assert main(["demo", "--root", str(ROOT), "--out", str(out)]) == 0
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "aerolito-legacy" in report
    assert "Verdict: PASS" in report
    assert "Verdict: READY" in report
    assert (out / "report.html").exists()
    assert (out / "trace.jsonl").exists()
    assert main(["report", "--root", str(ROOT), "--out", str(tmp_path / "report")]) == 0
    assert main(["scan", str(ROOT / "examples" / "aerolito_manifest.yaml")]) == 0
    assert main(["plan", str(ROOT / "examples" / "aerolito_manifest.yaml"), "--blast", "ds.raw.clicks"]) == 0
    assert (
        main(
            [
                "parity",
                str(ROOT / "examples" / "parity_legacy.json"),
                str(ROOT / "examples" / "parity_target.json"),
            ]
        )
        == 0
    )
    assert main(["migrate", str(ROOT / "examples" / "aerolito_registry.json")]) == 0
    assert main(["gate", str(ROOT / "examples" / "aerolito_gate.yaml")]) == 0
    assert main(["scan", str(tmp_path / "missing.yaml")]) == 2
    assert main(["eval", "--root", str(tmp_path)]) == 1
    assert main(["eval-regression", "--root", str(tmp_path)]) == 2
    assert main(["demo", "--root", str(tmp_path), "--out", str(tmp_path / "nope")]) == 2


def test_cli_exit_codes_for_gate_and_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    legacy = tmp_path / "legacy.json"
    target = tmp_path / "target.json"
    rows = [{"measure": 1.0}, {"measure": 2.0}]
    legacy.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    target.write_text(json.dumps({"rows": [{**row, "extra": 1} for row in rows]}), encoding="utf-8")
    assert main(["parity", str(legacy), str(target)]) == 3
    target.write_text(json.dumps({"rows": [{"measure": 1.0}]}), encoding="utf-8")
    assert main(["parity", str(legacy), str(target)]) == 1
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        """
parity_verdict: FAIL
parity_approved_by: null
rollback_plan_present: true
open_high_risks: 0
controls:
  - id: inventory.complete
    title: Inventory
    required: true
    status: pass
    approver: null
    evidence: synthetic
""",
        encoding="utf-8",
    )
    assert main(["gate", str(gate)]) == 1
    cyclic = tmp_path / "cycle.json"
    cyclic.write_text(
        json.dumps(
            manifest(
                datasets=[
                    dataset("ds.cycle.left", upstream=["ds.cycle.right"]),
                    dataset("ds.cycle.right", upstream=["ds.cycle.left"]),
                ]
            )
        ),
        encoding="utf-8",
    )
    assert main(["plan", str(cyclic)]) == 1
    monkeypatch.setenv("MLMIG_PROVIDER", "real")
    assert main(["demo", "--root", str(ROOT), "--out", str(tmp_path / "blocked")]) == 2
    monkeypatch.setenv("MLMIG_PROVIDER", "fake")
    monkeypatch.setenv("MLMIG_CASSETTE_RECORD", "1")
    assert main(["demo", "--root", str(ROOT), "--out", str(tmp_path / "record")]) == 2
    monkeypatch.delenv("MLMIG_CASSETTE_RECORD")
    monkeypatch.setenv("MLMIG_LOG_LEVEL", "LOUD")
    assert main(["scan", str(ROOT / "examples" / "aerolito_manifest.yaml")]) == 2


def test_provider_and_cassette(tmp_path: Path) -> None:
    fake = build_provider(Settings(provider="fake"), responses={"ping": {"ok": True}})
    assert isinstance(fake, FakeProvider)
    assert fake.fetch("ping", {"n": 1}) == {"ok": True}
    assert fake.network_calls == 0
    with pytest.raises(KeyError):
        fake.fetch("missing", {})
    with pytest.raises(ProviderDisabled):
        build_provider(Settings(provider="real"))
    with pytest.raises(ProviderDisabled):
        build_provider(Settings(cassette_record=True))
    with pytest.raises(ValueError):
        build_provider(Settings(provider="cassette"))
    cassette = Cassette(
        "unit",
        (Interaction("ping", {"n": 1}, {"ok": True}),),
    )
    path = tmp_path / "cassette.json"
    write_cassette(path, cassette)
    provider = CassetteProvider.load(path)
    assert provider.fetch("ping", {"n": 1})["ok"] is True
    with pytest.raises(CassetteMismatch):
        provider.fetch("ping", {"n": 1})

    def boom() -> tuple[bool, str]:
        raise RuntimeError("nope")

    results = run_invariants((("boom", boom),))
    assert results[0].passed is False
    assert results[0].name == "boom"


def test_gate_edges() -> None:
    control = Control("inventory.complete", "Inventory", True, "bogus", None, "")
    result = evaluate(
        GateInput(
            controls=(control,),
            parity_verdict="PASS",
            parity_approved_by=None,
            rollback_plan_present=True,
            open_high_risks=-1,
        )
    )
    assert result.verdict == "NOT_READY"
    pending = evaluate(
        GateInput(
            controls=(Control("inventory.complete", "Inventory", True, "pending", None, ""),),
            parity_verdict="PASS",
            parity_approved_by=None,
            rollback_plan_present=True,
            open_high_risks=0,
        )
    )
    assert pending.verdict == "NOT_READY"


def test_scan_retries_transient_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest(datasets=[dataset("ds.raw.one")])), encoding="utf-8")
    calls = {"n": 0}
    real = Path.read_text

    def flaky(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            calls["n"] += 1
            if calls["n"] < 3:
                raise PermissionError("busy")
        return real(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", flaky)
    scanned = scan_path(path, max_attempts=3, base_delay_s=0, backoff_cap_s=0, sleep=lambda _delay: None)
    assert scanned.ok
    assert calls["n"] == 3


def test_module_entrypoint_regression_exits_one() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "migration_eval", "platform-migrations", "eval-regression", "--root", str(ROOT)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["gate_went_red"] is True
    assert payload["verdict"] == "FAIL"


def test_commands_do_not_connect(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail_connect(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("socket connect is disabled")

    monkeypatch.setattr(socket.socket, "connect", fail_connect)
    monkeypatch.setattr(socket, "create_connection", fail_connect)
    assert main(["eval", "--root", str(ROOT)]) == 0
    assert main(["demo", "--root", str(ROOT), "--out", str(tmp_path / "offline")]) == 0
