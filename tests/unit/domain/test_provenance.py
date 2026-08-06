from pathlib import Path

import pytest

from datp_core.domain.provenance import canonical_value
from datp_core.domain.values.counts import RowCount


def test_canonical_value_is_deterministic_finite_and_strict() -> None:
    document = canonical_value({"z": RowCount(2), "a": Path("data/value.json")})
    assert isinstance(document, dict)
    assert tuple(document) == ("a", "z")
    assert document == {"a": "data/value.json", "z": 2}
    assert canonical_value((RowCount(1), RowCount(2))) == (1, 2)
    with pytest.raises(ValueError, match="non-finite"):
        canonical_value(float("nan"))
    with pytest.raises(TypeError, match="keys must be strings"):
        canonical_value({1: "invalid"})
