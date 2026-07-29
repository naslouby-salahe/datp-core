from pathlib import Path

import pytest

from datp_core.datasets.edge_iiotset.schema import EDGE_BENIGN_SENSOR_GROUPS
from datp_core.domain.errors import CapabilityError
from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.values import Seed
from datp_core.populations.edge_sensor_groups import (
    build_edge_sensor_groups,
    reject_attack_sensitive_request,
    reject_family_thresholding,
)


def test_edge_static_includes_ten_groups_with_modbus(edge_canonical_root: Path) -> None:
    manifest, membership = build_edge_sensor_groups(
        edge_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    assert manifest.document.accepted_clients == tuple(sorted(EDGE_BENIGN_SENSOR_GROUPS))
    assert "Modbus" in manifest.document.accepted_clients
    assert membership.get_column("client_id").n_unique() == 10
    assert manifest.document.attack_row_count == 0


def test_edge_static_rejects_attack_and_family_requests() -> None:
    with pytest.raises(CapabilityError):
        reject_attack_sensitive_request()
    with pytest.raises(CapabilityError):
        reject_family_thresholding()
