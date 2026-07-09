"""Validates docs/protocol/scope_boundaries.md (P0-T01)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "scope_boundaries.md"

FORBIDDEN_CLAIM_TERMS = [
    "solves non-IID",
    "privacy-preserving",
    "concept-drift handling",
    "fleet-scale validated",
]


def _sb_ids() -> list[str]:
    text = DOC.read_text()
    return re.findall(r"^- (SB-\d\d)\.", text, flags=re.MULTILINE)


def test_all_SB_ids_present_and_unique() -> None:
    ids = _sb_ids()
    expected = [f"SB-{i:02d}" for i in range(1, 33)]
    assert ids == expected


NEGATION_MARKERS = ("do not", "never", "without formal")


def test_forbidden_terms_absent() -> None:
    """Forbidden terms may appear only in a negated bullet or the catalog section."""
    body = DOC.read_text().split("## Forbidden Claim Terms", 1)[0]
    for line in body.splitlines():
        lowered = line.lower()
        for term in FORBIDDEN_CLAIM_TERMS:
            if term in lowered:
                assert any(marker in lowered for marker in NEGATION_MARKERS), (
                    f"forbidden claim term used outside a negation: {term!r} in {line!r}"
                )
