from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.preprocessing import validate_train_fit_split
from datp_core.domain.data.splitting import BenignCalibrationSplitSpec, TestSplitSpec, TrainingSplitSpec
from datp_core.domain.errors import DomainValidationError


def _fingerprint(value: int) -> StageFingerprint:
    return StageFingerprint(value=f"{value:064x}")


@given(st.integers(min_value=0, max_value=(1 << 60) - 1))
def test_train_only_fit_authorization_rejects_generated_non_training_splits(seed: int) -> None:
    partition = PartitionIdentity(value=_fingerprint(seed))
    training = TrainingSplitSpec(
        split_identity=SplitIdentity(value=_fingerprint(seed + 1)), partition_identity=partition
    )
    calibration = BenignCalibrationSplitSpec(
        split_identity=SplitIdentity(value=_fingerprint(seed + 2)), partition_identity=partition
    )
    test = TestSplitSpec(split_identity=SplitIdentity(value=_fingerprint(seed + 3)), partition_identity=partition)

    assert validate_train_fit_split(split=training) is training
    for split in (calibration, test):
        try:
            validate_train_fit_split(split=split)
        except DomainValidationError:
            continue
        raise AssertionError("non-training split was accepted for preprocessing fit")
