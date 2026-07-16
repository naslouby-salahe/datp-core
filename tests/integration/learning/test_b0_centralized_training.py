import pytest
import torch

from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
    CheckpointIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError, TrainingError
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.learning.centralized.nbaiot_b0_training import (
    CentralizedPooledBenignTrainingExecutor,
)


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _comparator() -> CentralizedModelComparatorSpec:
    return CentralizedModelComparatorSpec(
        model_identity=CentralizedModelIdentity(value=_fingerprint("1")),
        checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("2")),
        calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("3")),
        test_score_identity=CentralizedTestScoringIdentity(value=_fingerprint("4")),
        threshold_identity=CentralizedThresholdIdentity(value=_fingerprint("5")),
        evaluation_identity=CentralizedEvaluationIdentity(value=_fingerprint("6")),
    )


def test_centralized_identities_are_structurally_distinct_from_fedavg_identities() -> None:
    assert CentralizedModelIdentity is not TrainingIdentity
    assert CentralizedCheckpointIdentity is not CheckpointIdentity
    comparator_field_types = {field.type for field in _comparator().__dataclass_fields__.values()}
    assert TrainingIdentity not in comparator_field_types
    assert CheckpointIdentity not in comparator_field_types


def test_executor_rejects_a_fedavg_identity_in_place_of_a_centralized_comparator() -> None:
    fedavg_training_identity = TrainingIdentity(value=_fingerprint("7"))

    with pytest.raises(DomainValidationError):
        CentralizedPooledBenignTrainingExecutor(comparator=fedavg_training_identity, seed=Seed(value=1))  # type: ignore[arg-type]


def test_executor_requires_sequential_epoch_numbers() -> None:
    executor = CentralizedPooledBenignTrainingExecutor(comparator=_comparator(), seed=Seed(value=1))
    pooled_batch = torch.rand(8, 115, dtype=torch.float32)

    executor.execute(pooled_benign_batch=pooled_batch, epoch_number=1)
    with pytest.raises(TrainingError):
        executor.execute(pooled_benign_batch=pooled_batch, epoch_number=3)


def test_executor_updates_parameters_deterministically_for_a_fixed_seed() -> None:
    pooled_batch = torch.rand(8, 115, dtype=torch.float32)
    first = CentralizedPooledBenignTrainingExecutor(comparator=_comparator(), seed=Seed(value=1))
    second = CentralizedPooledBenignTrainingExecutor(comparator=_comparator(), seed=Seed(value=1))

    first.execute(pooled_benign_batch=pooled_batch, epoch_number=1)
    second.execute(pooled_benign_batch=pooled_batch, epoch_number=1)

    for left, right in zip(first.current_parameters(), second.current_parameters(), strict=True):
        assert torch.equal(left, right)
