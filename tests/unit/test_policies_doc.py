"""Validates docs/protocol/policies.md (P0-T04)."""

from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "policies.md"


def test_no_stale_labels() -> None:
    text = DOC.read_text()
    tables = text.split("## Naming Locks", 1)[0]
    assert "| B5 |" not in tables
    assert "| B3-LGS |" not in tables
    assert "No `B5` label exists" in text
    assert "No `B3-LGS` label exists" in text


def test_b0_not_in_causal_ladder() -> None:
    text = DOC.read_text()
    assert "**not in the FL causal ladder**" in text
    assert "| B0 |" in text


def test_b4_canonical_k_is_3() -> None:
    text = DOC.read_text()
    assert "canonical K = 3" in text
    assert "K = 9 and other K are exploratory" in text


def test_fallback_not_named_ditto() -> None:
    text = DOC.read_text()
    assert 'never labeled "Ditto"' in text
    assert "FedRep-AE" in text and "FedPer-AE" in text
