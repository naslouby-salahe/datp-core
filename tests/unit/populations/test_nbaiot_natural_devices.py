from pathlib import Path

from datp_core.datasets.nbaiot.schema import NBAIOT_DEVICE_IDENTITIES
from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.values import Seed
from datp_core.populations.nbaiot_natural_devices import build_nbaiot_natural_devices


def test_natural_devices_are_exactly_the_audited_nine(nbaiot_canonical_root: Path) -> None:
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    assert manifest.document.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert manifest.document.accepted_clients == tuple(sorted(NBAIOT_DEVICE_IDENTITIES))
    assert len(manifest.document.accepted_clients) == 9
    assert membership.get_column("client_id").n_unique() == 9
    assert set(manifest.family_by_client)  # families present
    assert manifest.document.benign_row_count == 9 * 30
    assert manifest.document.attack_row_count == 9 * 12
    assert membership.height == manifest.document.total_membership_rows


def test_natural_devices_replay_is_deterministic(nbaiot_canonical_root: Path) -> None:
    first, first_membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(3), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    second, second_membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(3), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    assert first.document == second.document
    assert first_membership.equals(second_membership)
