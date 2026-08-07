"""Scientific contract: one frozen detector and score inventory serves every threshold method."""

import dataclasses
from pathlib import Path

import polars as pl
from sklearn.metrics import roc_auc_score
from tests.unit.learning.federated.helpers import AUTOENCODER, BATCH_SIZE, FEATURE_NAMES, benign_frame, client_identity
from tests.unit.scoring.helpers import selected_checkpoint

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.domain.enums import ScoreFrameColumn
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    CheckpointDecision,
    FederatedTrainingCoordinate,
)
from datp_core.pipeline.scoring.federated import publish_federated_scores
from datp_core.pipeline.scoring.models import ClientScoringInput, GenerateFederatedScoresRequest, ScoreGenerationRequest
from datp_core.protocols.inference import FixedScoreInvariant, ScoreArtifactManifest, ScoreRecord


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


def test_score_generation_request_has_no_threshold_identity_field() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(ScoreGenerationRequest))
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def test_score_artifact_manifest_has_no_threshold_identity_field() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(ScoreArtifactManifest))
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def test_fixed_score_invariant_has_no_threshold_identity_field() -> None:
    field_names = frozenset(field.name for field in dataclasses.fields(FixedScoreInvariant))
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


def _scored_result(tmp_path: Path):
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    clients = (
        ClientScoringInput(
            client=client_identity("client_a"),
            calibration_features=benign_frame(RowCount(8), seed=Seed(1)),
            evaluation_features=_evaluation_frame(),
        ),
    )
    result = publish_federated_scores(
        GenerateFederatedScoresRequest(
            checkpoint=checkpoint,
            scored_split_protocol=checkpoint.coordinate.split_protocol,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            clients=clients,
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
            split_manifest_checksum=checkpoint.split_manifest_checksum,
            overwrite=False,
        )
    )
    return checkpoint, result


def test_every_threshold_method_receives_identical_detector_provenance(tmp_path: Path) -> None:
    checkpoint, result = _scored_result(tmp_path)
    invariant = FixedScoreInvariant.from_manifest(result.manifest)

    assert invariant.model_checksum == checkpoint.tensor_checksum
    assert invariant.preprocessing_state_set_checksum == checkpoint.preprocessing_state_set_checksum
    assert invariant.split_manifest_checksum == checkpoint.split_manifest_checksum
    assert invariant.calibration_score_set_checksum == result.invariant.calibration_score_set_checksum
    assert invariant.evaluation_score_set_checksum == result.invariant.evaluation_score_set_checksum


def _auroc_from_evaluation_records(manifest) -> float:
    frame = pl.read_parquet(manifest.evaluation_records[0].path)
    label_column = ScoreFrameColumn.OUTCOME_LABEL.value
    score_column = ScoreFrameColumn.RECONSTRUCTION_ERROR.value
    labels = tuple(
        1 if label == PopulationOutcomeLabel.ATTACK.value else 0 for label in frame.get_column(label_column).to_list()
    )
    scores = tuple(float(score) for score in frame.get_column(score_column).to_list())
    return float(roc_auc_score(labels, scores))


def test_auroc_is_identical_across_independently_generated_score_artifacts(tmp_path: Path) -> None:
    _checkpoint_a, result_a = _scored_result(tmp_path / "run_a")
    _checkpoint_b, result_b = _scored_result(tmp_path / "run_b")

    auroc_a = _auroc_from_evaluation_records(result_a.manifest)
    auroc_b = _auroc_from_evaluation_records(result_b.manifest)

    assert auroc_a == auroc_b


def test_rescoring_the_same_frozen_checkpoint_reproduces_byte_identical_score_artifacts(tmp_path: Path) -> None:
    checkpoint, first_result = _scored_result(tmp_path / "run_a")
    first_bytes = first_result.manifest.evaluation_records[0].path.read_bytes()

    request = GenerateFederatedScoresRequest(
        checkpoint=checkpoint,
        scored_split_protocol=checkpoint.coordinate.split_protocol,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=(
            ClientScoringInput(
                client=client_identity("client_a"),
                calibration_features=benign_frame(RowCount(8), seed=Seed(1)),
                evaluation_features=_evaluation_frame(),
            ),
        ),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "run_b" / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
        overwrite=False,
    )
    second_result = publish_federated_scores(request)
    second_bytes = second_result.manifest.evaluation_records[0].path.read_bytes()

    assert second_bytes == first_bytes
    assert FixedScoreInvariant.from_manifest(second_result.manifest) == FixedScoreInvariant.from_manifest(
        first_result.manifest
    )
