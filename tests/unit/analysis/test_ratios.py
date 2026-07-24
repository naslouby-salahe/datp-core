"""`materiality_threshold` mechanically extracts its numeric value from the authored rule name,
rather than duplicating that value as a separately hardcoded literal -- so a change to the
configured threshold is picked up without a code change, and an unsupported name fails loudly."""

import pytest

from datp_core.analysis.ratios import materiality_threshold


def test_numeric_rule_is_returned_directly() -> None:
    assert materiality_threshold(1.0e-5) == 1.0e-5
    assert materiality_threshold(5) == 5.0


def test_named_rule_value_is_parsed_from_its_own_name() -> None:
    assert materiality_threshold("absolute_denominator_at_least_1.0e-6") == pytest.approx(1.0e-6)
    assert materiality_threshold("absolute_denominator_at_least_5") == pytest.approx(5.0)
    assert materiality_threshold("absolute_denominator_at_least_0.001") == pytest.approx(0.001)


def test_unsupported_rule_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported denominator materiality rule"):
        materiality_threshold("some_other_rule")
