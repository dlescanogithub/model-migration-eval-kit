"""Lightweight secret scan. Vendored and kept identical across portfolio repos.

Not a substitute for a dedicated scanner. Patterns are assembled from pieces so
this file does not contain a literal key.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_PRIVATE_KEY = "-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
_AWS = "AKIA" + r"[0-9A-Z]{16}"
_ANTHROPIC = "sk-ant-" + r"[A-Za-z0-9_\-]{20,}"
_OPENAI = "sk-" + r"(?!ant-)[A-Za-z0-9_\-]{20,}"
_ELEVENLABS = "sk_" + r"[A-Za-z0-9]{20,}"
_GITHUB_PAT = "github_pat_" + r"[A-Za-z0-9_]{20,}"
_GITHUB = "ghp_" + r"[A-Za-z0-9]{20,}"
_XAI = "xai-" + r"[A-Za-z0-9_\-]{20,}"
_BEARER = "Bearer " + r"[A-Za-z0-9._~\-+/]{20,}"

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(_PRIVATE_KEY)),
    ("aws_access_key", re.compile(_AWS)),
    ("anthropic_key", re.compile(_ANTHROPIC)),
    ("openai_key", re.compile(_OPENAI)),
    ("elevenlabs_key", re.compile(_ELEVENLABS)),
    ("github_pat", re.compile(_GITHUB_PAT)),
    ("github_token", re.compile(_GITHUB)),
    ("xai_key", re.compile(_XAI)),
    ("bearer_token", re.compile(_BEARER)),
)

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "out",
        "var",
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

_DOCUMENTED_HASH = re.compile(r"secretscan\.py sha256:\s*([0-9a-f]{64})")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.kind}"


def module_sha256() -> str:
    """Digest of this file. Portfolio repos keep the same bytes and the same digest."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def documented_sha256(provenance: Path) -> str:
    match = _DOCUMENTED_HASH.search(provenance.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"{provenance} is missing the secretscan.py sha256 line")
    return match.group(1)


def hash_matches(provenance: Path) -> bool:
    return documented_sha256(provenance) == module_sha256()


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
