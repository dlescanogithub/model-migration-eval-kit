"""Lightweight secret scan for the repo. Not a substitute for a dedicated scanner."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Patterns are assembled so this file does not contain a literal secret shape.
_INLINE_TOKEN = "x-access-" + "token:" + r"[^@\s]+@"
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile("AKIA" + r"[0-9A-Z]{16}")),
    ("openai_key", re.compile("sk-" + r"[A-Za-z0-9]{20,}")),
    ("github_token", re.compile("ghp_" + r"[A-Za-z0-9]{20,}")),
    ("github_pat", re.compile("github_pat_" + r"[A-Za-z0-9_]{20,}")),
    ("slack_token", re.compile("xox" + r"[baprs]-[A-Za-z0-9-]{10,}")),
    ("inline_token_url", re.compile(_INLINE_TOKEN)),
)

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "out",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "htmlcov",
        "dist",
        "build",
        ".eggs",
    }
)

_PLACEHOLDER_HINTS: tuple[str, ...] = (
    "changeme",
    "your-api-key",
    "your-key",
    "example",
    "placeholder",
    "redacted",
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.kind}"


def scan_path(root: Path) -> list[Finding]:
    """Scan text files under root. Returns findings, empty when clean."""
    findings: list[Finding] = []
    if root.is_file():
        findings.extend(_scan_file(root, root))
        return findings
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pyc", ".whl"}:
            continue
        findings.extend(_scan_file(path, root))
    return findings


def _scan_file(path: Path, root: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    relative = str(path.relative_to(root) if path.is_relative_to(root) else path)
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _is_placeholder(line):
            continue
        for kind, pattern in _PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path=relative, line=line_number, kind=kind))
    return findings


def _is_placeholder(line: str) -> bool:
    lowered = line.lower()
    return any(hint in lowered for hint in _PLACEHOLDER_HINTS)
