from pathlib import Path

import pytest
from tests.unit.centralized_reference.helpers import (
    AUTOENCODER,
    CHECKPOINT,
    FEATURE_NAMES,
    SEED,
    benign_frame,
    fitted_state,
    mixed_evaluation_frame,
    require_cuda,
    training_coordinate,
)

from datp_core.centralized_reference.checkpointing import FederatedCheckpointMarker, reject_federated_checkpoint
from datp_core.centralized_reference.thresholding import CENTRALIZED_POOLED_QUANTILE_PROTOCOL
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import Checksum
from datp_core.orchestration.stages.construct_centralized_reference_threshold import (
    ConstructCentralizedThresholdRequest,
    construct_centralized_reference_threshold_stage,
)
from datp_core.orchestration.stages.evaluate_centralized_reference import (
    EvaluateCentralizedReferenceRequest,
    evaluate_centralized_reference_stage,
)
from datp_core.orchestration.stages.score_centralized_reference import (
    ScoreCentralizedReferenceRequest,
    score_centralized_reference_stage,
)
from datp_core.orchestration.stages.select_centralized_reference_checkpoint import (
    SelectCentralizedCheckpointRequest,
    select_centralized_reference_checkpoint_stage,
)
from datp_core.orchestration.stages.train_centralized_reference import (
    TrainCentralizedReferenceRequest,
    train_centralized_reference_stage,
)
from datp_core.protocols.training import BATCH_SIZE as DECLARED_BATCH_SIZE


def test_train_score_threshold_evaluate_stage_chain(tmp_path: Path) -> None:
    require_cuda()
    coordinate = training_coordinate()
    state = fitted_state(tmp_path / "state.skops")
    train_result = train_centralized_reference_stage(
        TrainCentralizedReferenceRequest(
            coordinate=coordinate,
            training_features=benign_frame(320, seed=0),
            feature_names=FEATURE_NAMES,
            preprocessing_state=state,
            split_manifest_checksum=Checksum("e" * 64),
            output_directory=tmp_path / "train",
            training_seed=SEED,
            autoencoder=AUTOENCODER,
            checkpoint_protocol=CHECKPOINT,
            overwrite=False,
        )
    )
    assert train_result.stage is StageOperationId.TRAIN_CENTRALIZED_REFERENCE
    assert train_result.publication_status is PublicationStatus.PUBLISHED
    assert len(train_result.candidates) == 1

    selection = select_centralized_reference_checkpoint_stage(
        SelectCentralizedCheckpointRequest(
            coordinate=coordinate,
            candidates=train_result.candidates,
            checkpoint_protocol=CHECKPOINT,
            preprocessing_checksum=state.estimator_checksum,
            split_checksum=Checksum("e" * 64),
            training_seed_value=SEED.value,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    )
    assert selection.decision.selected.round_number == CHECKPOINT.maximum_round
    assert selection.decision.selection_rule.value == "fixed_terminal_maximum_round"

    score_result = score_centralized_reference_stage(
        ScoreCentralizedReferenceRequest(
            coordinate=coordinate,
            checkpoint=selection.decision.selected,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(48, seed=20),
            evaluation_features=mixed_evaluation_frame(40, seed=21),
            batch_size=DECLARED_BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_checksum=state.estimator_checksum,
            overwrite=False,
        )
    )
    assert score_result.stage is StageOperationId.SCORE_CENTRALIZED_REFERENCE

    threshold_result = construct_centralized_reference_threshold_stage(
        ConstructCentralizedThresholdRequest(
            coordinate=coordinate,
            calibration_scores=score_result.scoring.calibration_scores,
            output_directory=tmp_path / "threshold",
            protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
            overwrite=False,
        )
    )
    assert threshold_result.stage is StageOperationId.CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD

    evaluation_result = evaluate_centralized_reference_stage(
        EvaluateCentralizedReferenceRequest(
            coordinate=coordinate,
            evaluation_scores=score_result.scoring.evaluation_scores,
            threshold=threshold_result.threshold,
            output_directory=tmp_path / "evaluation",
            overwrite=False,
        )
    )
    assert evaluation_result.stage is StageOperationId.EVALUATE_CENTRALIZED_REFERENCE
    assert evaluation_result.evaluation.is_confirmatory_ladder_member is False

    reused = train_centralized_reference_stage(
        TrainCentralizedReferenceRequest(
            coordinate=coordinate,
            training_features=benign_frame(320, seed=0),
            feature_names=FEATURE_NAMES,
            preprocessing_state=state,
            split_manifest_checksum=Checksum("e" * 64),
            output_directory=tmp_path / "train",
            training_seed=SEED,
            autoencoder=AUTOENCODER,
            checkpoint_protocol=CHECKPOINT,
            overwrite=False,
        )
    )
    assert reused.publication_status is PublicationStatus.REUSED


def test_score_stage_rejects_federated_checkpoint(tmp_path: Path) -> None:
    with pytest.raises(LeakageError, match="federated checkpoint"):
        reject_federated_checkpoint(FederatedCheckpointMarker("fedavg", tmp_path / "m.pt"))
