"""Validates docs/protocol/regimes.md (P0-T03)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "regimes.md"

REGIME_HEADINGS = [
    "Regime A",
    "Regime B-a",
    "Regime B-b",
    "Regime C",
    "Regime D",
    "Regime D-temporal",
]


def test_all_regimes_have_role_and_passrule() -> None:
    text = DOC.read_text()
    sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    found = [s.split(" —", 1)[0].strip() for s in sections if s.split("\n", 1)[0].startswith("Regime")]
    assert found == REGIME_HEADINGS
    for section in sections:
        if not section.split("\n", 1)[0].startswith("Regime"):
            continue
        assert "**Role:**" in section
        assert "rule:**" in section  # Pass/fail/suppression or Rejection rule


def test_bb_marked_rejected() -> None:
    text = DOC.read_text()
    section = re.search(r"## Regime B-b —.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert section is not None
    assert "**Role:** `rejected`" in section.group(0)
    assert "B_B_REJECTED_NO_METADATA" in section.group(0)


def test_no_quantitative_bb_claim() -> None:
    text = DOC.read_text()
    section = re.search(r"## Regime B-b —.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert section is not None
    assert "**Primary metric:**" not in section.group(0)
