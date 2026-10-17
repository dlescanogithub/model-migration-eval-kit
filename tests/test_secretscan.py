"""Secret-shape fixtures are built at runtime so the repo never stores a literal key."""

from __future__ import annotations

from pathlib import Path

from migration_eval.paths import repo_root
from migration_eval.secretscan import hash_matches, scan_path


def _join(*parts: str) -> str:
    return "".join(parts)


def _scan_line(tmp_path: Path, line: str) -> set[str]:
    target = tmp_path / "notes.txt"
    target.write_text(line + "\n", encoding="utf-8")
    return {finding.kind for finding in scan_path(target)}


def test_each_required_shape_matches_and_short_values_do_not(tmp_path: Path) -> None:
    samples = {
        "private_key": _join("-----BEGIN ", "PRIVATE KEY-----"),
        "aws_access_key": _join("AKIA", "A" * 16),
        "anthropic_key": _join("sk-ant-", "a" * 24),
        "openai_key": _join("sk-", "b" * 24),
        "elevenlabs_key": _join("sk_", "c" * 24),
        "github_pat": _join("github_pat_", "d" * 22),
        "github_token": _join("ghp_", "e" * 24),
        "xai_key": _join("xai-", "f" * 24),
        "bearer_token": _join("Bearer ", "g" * 24),
    }
    for kind, line in samples.items():
        assert kind in _scan_line(tmp_path, line)

    shorts = (
        _join("-----BEGIN ", "PUBLIC KEY-----"),
        _join("AKIA", "A" * 15),
        _join("sk-ant-", "a" * 10),
        _join("sk-", "b" * 10),
        _join("sk_", "c" * 10),
        _join("github_pat_", "d" * 8),
        _join("ghp_", "e" * 8),
        _join("xai-", "f" * 8),
        _join("Bearer ", "short"),
        "ordinary ticket text",
    )
    for line in shorts:
        assert _scan_line(tmp_path, line) == set()


def test_prefix_kinds_do_not_steal_each_other(tmp_path: Path) -> None:
    anthropic = _scan_line(tmp_path, _join("sk-ant-", "h" * 24))
    assert anthropic == {"anthropic_key"}
    project = _scan_line(tmp_path, _join("sk-proj-", "i" * 24))
    assert project == {"openai_key"}
    rsa = _scan_line(tmp_path, _join("-----BEGIN ", "RSA ", "PRIVATE KEY-----"))
    assert rsa == {"private_key"}


def test_placeholder_lines_are_skipped(tmp_path: Path) -> None:
    line = "token = " + _join("sk-", "j" * 24) + " example"
    assert _scan_line(tmp_path, line) == set()


def test_ci_workflow_does_not_enable_live_mode() -> None:
    text = (repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "LIVE_MODE=1" not in text
    assert "MIGRATION_EVAL_ENABLE_LIVE" not in text


def test_documented_secretscan_hash_matches_the_file() -> None:
    assert hash_matches(repo_root() / "docs" / "PROVENANCE.md")
