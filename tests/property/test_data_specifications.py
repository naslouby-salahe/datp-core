from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.splitting import (
    BenignCalibrationSplitSpec,
    SplitCollectionSpec,
    TestSplitSpec,
    TrainingSplitSpec,
)


def _fingerprint(value: int) -> StageFingerprint:
    return StageFingerprint(value=f"{value:064x}")


@given(st.integers(min_value=0, max_value=(1 << 60) - 1))
def test_split_collection_has_exactly_one_non_overlapping_member_of_each_static_role(seed: int) -> None:
    partition_identity = PartitionIdentity(value=_fingerprint(seed))
    collection = SplitCollectionSpec(
        training=TrainingSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint(seed + 1)), partition_identity=partition_identity
        ),
        calibration=BenignCalibrationSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint(seed + 2)), partition_identity=partition_identity
        ),
        test=TestSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint(seed + 3)),
            partition_identity=partition_identity,
        ),
    )

    members = (collection.training, collection.calibration, collection.test)

    assert sum(isinstance(member, TrainingSplitSpec) for member in members) == 1
    assert sum(isinstance(member, BenignCalibrationSplitSpec) for member in members) == 1
    assert sum(isinstance(member, TestSplitSpec) for member in members) == 1
    assert len({member.split_identity for member in members}) == 3
