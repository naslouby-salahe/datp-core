"""Validates docs/protocol/seed_plan.md (P0-T07)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "seed_plan.md"


def test_ten_paired_seeds() -> None:
    text = DOC.read_text()
    match = re.search(r"\{0, 1, 2, 3, 4, 5, 6, 7, 8, 9\}", text)
    assert match is not None
    assert "## Pairing Rule" in text


def test_seed_extension_rule_present() -> None:
    text = DOC.read_text()
    assert "## Seed-Extension Honesty Rule (Locked)" in text
    assert "[0.647, 0.769]" in text
    assert "never suppressed when it is less favorable" in text


def test_no_seed_dropping_allowed() -> None:
    text = DOC.read_text()
    assert "## No Seed Dropping" in text
    assert "not silently removed" in text
