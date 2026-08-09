import pytest

from datp_core.core.identifiers import ClientIdentityToken
from datp_core.core.numeric import ClientCount, DirichletConcentration
from datp_core.data.populations.contracts import (
    ControlledPartitionCondition,
    ControlledPartitionKind,
    dirichlet_condition,
    iid_condition,
    synthetic_client_ids,
)


def test_controlled_partition_kind_member_set_is_exact_and_unique() -> None:
    assert set(ControlledPartitionKind.__members__) == {"DIRICHLET", "IID"}
    values = tuple(member.value for member in ControlledPartitionKind)
    assert len(values) == len(set(values))
    assert all(value.islower() for value in values)


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
    assert ids[0] == ClientIdentityToken("synthetic_client_00")
    assert ids[-1] == ClientIdentityToken("synthetic_client_19")
    assert len(set(ids)) == 20
