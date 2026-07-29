from pathlib import Path

import pytest

from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.errors import CapabilityError
from datp_core.domain.values import Seed
from datp_core.populations.ciciot_file_clients import (
    build_ciciot_file_clients,
    reject_family_interpretation,
    reject_physical_device_interpretation,
)


def test_ciciot_builds_exactly_sixty_three_file_clients(ciciot_canonical_root: Path) -> None:
    manifest, membership = build_ciciot_file_clients(
        ciciot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    assert len(manifest.document.accepted_clients) == 63
    assert membership.get_column("client_id").n_unique() == 63
    # ineligible row from Merged01 local=8 is excluded
    assert membership.height == 63 * 9 - 1


def test_ciciot_rejects_physical_family_and_temporal_interpretation(ciciot_canonical_root: Path) -> None:
    with pytest.raises(CapabilityError):
        reject_physical_device_interpretation()
    with pytest.raises(CapabilityError):
        reject_family_interpretation()
    with pytest.raises(CapabilityError):
        build_ciciot_file_clients(
            ciciot_canonical_root,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        )
