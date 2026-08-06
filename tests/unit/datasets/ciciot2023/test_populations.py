from pathlib import Path

import pytest

from datp_core.datasets.ciciot2023.populations import (
    construct_ciciot_file_clients,
    reject_family_interpretation,
    reject_physical_device_interpretation,
)
from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.errors import CapabilityError
from datp_core.domain.values.counts import Seed


def test_ciciot_builds_exactly_sixty_three_file_clients(ciciot_canonical_root: Path) -> None:
    construction = construct_ciciot_file_clients(
        ciciot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
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
        construct_ciciot_file_clients(
            ciciot_canonical_root,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        )


def test_ciciot_excluded_rows_preserve_typed_canonical_reasons(ciciot_canonical_root: Path) -> None:
    construction = construct_ciciot_file_clients(
        ciciot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    evidence = construction.evidence
    assert evidence is not None
    excluded_rows, per_client = evidence.excluded_rows, evidence.client_eligibility

    assert excluded_rows.height == 1
    assert excluded_rows.get_column("nonfinite_feature").to_list() == [True]
    assert excluded_rows.get_column("missing_or_unrecognized_label").to_list() == [False]
    assert per_client.get_column("excluded_row_count").to_list() == [1]
    assert per_client.get_column("nonfinite_feature").to_list() == [1]
