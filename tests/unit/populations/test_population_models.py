import pytest

from datp_core.domain.enums import ControlledPartitionKind
from datp_core.domain.values import ClientCount, DirichletConcentration
from datp_core.populations.models import (
    ControlledPartitionCondition,
    dirichlet_condition,
    hamilton_integer_counts,
    iid_condition,
    synthetic_client_ids,
)


def test_hamilton_allocation_conserves_rows_and_is_deterministic() -> None:
    assert hamilton_integer_counts(10, (1 / 3, 1 / 3, 1 / 3)) == (4, 3, 3)
    assert hamilton_integer_counts(11, (1 / 3, 1 / 3, 1 / 3)) == (4, 4, 3)
    temporal = hamilton_integer_counts(100, (0.55, 0.15, 0.10, 0.20))
    assert sum(temporal) == 100
    assert temporal == (55, 15, 10, 20)


def test_hamilton_rejects_invalid_ratios() -> None:
    with pytest.raises(ValueError):
        hamilton_integer_counts(10, (0.5, 0.5, 0.5))
    with pytest.raises(ValueError):
        hamilton_integer_counts(-1, (1.0,))


def test_controlled_partition_conditions_separate_iid_from_dirichlet() -> None:
    iid = iid_condition()
    assert iid.kind is ControlledPartitionKind.IID
    assert iid.concentration is None
    dirichlet = dirichlet_condition(DirichletConcentration(0.5))
    assert dirichlet.kind is ControlledPartitionKind.DIRICHLET
    assert dirichlet.concentration == DirichletConcentration(0.5)
    with pytest.raises(ValueError):
        ControlledPartitionCondition(ControlledPartitionKind.DIRICHLET, None)
    with pytest.raises(ValueError):
        ControlledPartitionCondition(ControlledPartitionKind.IID, DirichletConcentration(1.0))


def test_synthetic_client_ids_are_stable_and_count_locked() -> None:
    ids = synthetic_client_ids(ClientCount(20))
    assert len(ids) == 20
    assert ids[0] == "synthetic_client_00"
    assert ids[-1] == "synthetic_client_19"
    assert len(set(ids)) == 20
