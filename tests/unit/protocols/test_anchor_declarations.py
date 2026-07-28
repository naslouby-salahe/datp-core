import pytest

from datp_core.domain.errors import UnresolvedScientificValueError
from datp_core.protocols.anchor import require_anchor_tolerances


def test_anchor_tolerances_remain_unresolved() -> None:
    with pytest.raises(UnresolvedScientificValueError):
        require_anchor_tolerances()
