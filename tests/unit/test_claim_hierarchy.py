"""Validates docs/protocol/claim_hierarchy.md (P0-T02)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "claim_hierarchy.md"

TIER_NAMES = [
    "Confirmatory",
    "Secondary Supportive",
    "External Validation",
    "Stress-Test",
    "Mechanism",
    "Boundary-Condition",
    "Exploratory",
    "Future Work",
    "Forbidden",
]


def _tier_headings() -> list[str]:
    text = DOC.read_text()
    return re.findall(r"^## Tier (\d) — ([^(\n]+)", text, flags=re.MULTILINE)


def test_single_confirmatory_tier1() -> None:
    text = DOC.read_text()
    heading_tags = re.findall(r"^## Tier \d.*\(role=(\w+)", text, flags=re.MULTILINE)
    assert heading_tags.count("confirmatory") == 1
    assert "## Tier 1 — Confirmatory (role=confirmatory, singular)" in text


def test_tier9_forbidden_enumerated() -> None:
    tiers = _tier_headings()
    assert len(tiers) == 9
    assert tiers[-1][0] == "9"
    assert "Forbidden" in tiers[-1][1]


def test_no_supportive_marked_confirmatory() -> None:
    text = DOC.read_text()
    for tier_num in range(2, 10):
        section = re.search(
            rf"## Tier {tier_num} —.*?(?=## Tier {tier_num + 1} —|\Z)",
            text,
            flags=re.DOTALL,
        )
        assert section is not None
        assert "role=confirmatory" not in section.group(0)
