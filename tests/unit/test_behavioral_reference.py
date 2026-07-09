"""Validates docs/protocol/behavioral_reference.md (P0-T10)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "behavioral_reference.md"

FORBIDDEN_PATH_PATTERNS = [
    r"src/datp/",
    r"\.py:\d+",
    r"from datp\.",
    r"import datp",
]

BACKWARD_COMPAT_TERMS = [
    "shim",
    "redirect",
    "backward compat",
    "backward-compat",
    "legacy support",
    "deprecated alias",
    "fake compatibility",
]


def test_no_source_paths_copied() -> None:
    text = DOC.read_text()
    for pattern in FORBIDDEN_PATH_PATTERNS:
        assert not re.search(pattern, text), f"source path/import leaked: {pattern!r}"


def test_no_backward_compat_language() -> None:
    text = DOC.read_text().lower()
    for term in BACKWARD_COMPAT_TERMS:
        assert term not in text
