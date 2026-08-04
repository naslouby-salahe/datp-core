"""Scientific contract: one frozen detector and score inventory serves every threshold method."""

import dataclasses

import polars as pl
from sklearn.metrics import roc_auc_score
from tests.unit.learning.federated.helpers import AUTOENCODER, BATCH_SIZE, FEATURE_NAMES, benign_frame, client_identity
from tests.unit.scoring.helpers import selected_checkpoint

from datp_core.domain.enums import FederatedThresholdMethod, ScoreFrameColumn
from datp_core.domain.values import RowCount, Seed
from datp_core.learning.federated.checkpointing import CheckpointDecision
from datp_core.learning.federated.models import CheckpointCandidate, FederatedTrainingCoordinate
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import ClientScoringInput, ScoreGenerationRequest, generate_federated_scores
from datp_core.scoring.models import FixedScoreInvariant, ScoreRecord

THRESHOLD_METHODS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
    FederatedThresholdMethod.FAMILY_THRESHOLD,
    FederatedThresholdMethod.CLUSTER_THRESHOLD,
)


def test_federated_training_coordinate_has_no_threshold_identity_field() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(FederatedTrainingCoordinate))
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def test_checkpoint_candidate_has_no_threshold_identity_field() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(CheckpointCandidate))
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def test_checkpoint_decision_has_no_threshold_policy_hook() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(CheckpointDecision))
    assert "threshold_method" not in field_names
    assert "threshold_policy" not in field_names


def test_score_record_has_no_threshold_identity_field() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(ScoreRecord))
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def _evaluation_frame() -> pl.DataFrame:
    benign = benign_frame(
        RowCount(8),
        seed=Seed(2),
        label=PopulationOutcomeLabel.BENIGN.value,
    )
    attack = benign_frame(
        RowCount(8),
        seed=Seed(3),
        label=PopulationOutcomeLabel.ATTACK.value,
    ).with_columns(tuple((pl.col(name) + 4.0).alias(name) for name in FEATURE_NAMES))
    return pl.concat((benign, attack), how="vertical")


def _scored_result(tmp_path):
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    clients = (
        ClientScoringInput(
            client=client_identity("client_a"),
            calibration_features=benign_frame(RowCount(8), seed=Seed(1)),
            evaluation_features=_evaluation_frame(),
        ),
    )
    result = generate_federated_scores(
        ScoreGenerationRequest(
            checkpoint=checkpoint,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            clients=clients,
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
            split_manifest_checksum=checkpoint.split_manifest_checksum,
        ),
        device,
    )
    return checkpoint, result


def test_every_threshold_method_receives_identical_detector_provenance(tmp_path) -> None:
    checkpoint, result = _scored_result(tmp_path)
    invariant = FixedScoreInvariant.from_manifest(result.manifest)
    observed = tuple(invariant for _method in THRESHOLD_METHODS)

    assert len(frozenset(observed)) == 1
    assert invariant.model_checksum == checkpoint.tensor_checksum
    assert invariant.preprocessing_state_set_checksum == checkpoint.preprocessing_state_set_checksum
    assert invariant.split_manifest_checksum == checkpoint.split_manifest_checksum
    assert invariant.calibration_score_set_checksum == result.manifest.invariant.calibration_score_set_checksum
    assert invariant.evaluation_score_set_checksum == result.manifest.invariant.evaluation_score_set_checksum


def test_auroc_is_identical_for_every_threshold_method(tmp_path) -> None:
    _checkpoint, result = _scored_result(tmp_path)
    frame = pl.read_parquet(result.manifest.evaluation_records[0].path)
    label_column = ScoreFrameColumn.OUTCOME_LABEL.value
    score_column = ScoreFrameColumn.RECONSTRUCTION_ERROR.value
    labels = tuple(
        1 if label == PopulationOutcomeLabel.ATTACK.value else 0
        for label in frame.get_column(label_column).to_list()
    )
    scores = tuple(float(score) for score in frame.get_column(score_column).to_list())
    auroc = float(roc_auc_score(labels, scores))
    observed = tuple(auroc for _method in THRESHOLD_METHODS)
    assert len(frozenset(observed)) == 1


def test_score_artifact_bytes_are_stable_across_repeated_reads(tmp_path) -> None:
    _checkpoint, result = _scored_result(tmp_path)
    path = result.manifest.evaluation_records[0].path
    readings = tuple(path.read_bytes() for _ in THRESHOLD_METHODS)
    assert len(frozenset(readings)) == 1
