"""Scientific contract: one FedAvg model/score pair is reusable across all threshold methods."""

import dataclasses

import polars as pl
from tests.unit.learning.federated.helpers import AUTOENCODER, BATCH_SIZE, FEATURE_NAMES, benign_frame, client_identity
from tests.unit.scoring.helpers import selected_checkpoint

from datp_core.learning.federated.checkpointing import CheckpointDecision
from datp_core.learning.federated.models import CheckpointCandidate, FederatedTrainingCoordinate
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import ClientScoringInput, ScoreGenerationRequest, generate_federated_scores
from datp_core.scoring.models import FixedScoreInvariant, ScoreRecord


def test_federated_training_coordinate_has_no_threshold_identity_field() -> None:
    field_names = {field.name for field in dataclasses.fields(FederatedTrainingCoordinate)}
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def test_checkpoint_candidate_has_no_threshold_identity_field() -> None:
    field_names = {field.name for field in dataclasses.fields(CheckpointCandidate)}
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def test_checkpoint_decision_has_no_threshold_policy_hook() -> None:
    """A checkpoint decision's typed fields carry no hook by which a threshold-policy
    identity could request a distinct model or a rescoring pass."""
    field_names = {field.name for field in dataclasses.fields(CheckpointDecision)}
    assert "threshold_method" not in field_names
    assert "threshold_policy" not in field_names


def test_score_record_has_no_threshold_identity_field() -> None:
    field_names = {field.name for field in dataclasses.fields(ScoreRecord)}
    assert "threshold_method" not in field_names
    assert "threshold_identity" not in field_names


def _scored_result(tmp_path):
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    clients = (
        ClientScoringInput(
            client=client_identity("client_a"),
            calibration_features=benign_frame(8, seed=1),
            evaluation_features=benign_frame(8, seed=2),
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


def test_every_simulated_threshold_method_reads_one_model_and_score_checksum(tmp_path) -> None:
    checkpoint, result = _scored_result(tmp_path)
    invariants_seen_by_threshold_method = {
        method: FixedScoreInvariant.from_manifest(result.manifest)
        for method in ("shared_threshold", "local_threshold", "cluster_threshold")
    }
    assert len(set(invariants_seen_by_threshold_method.values())) == 1
    assert result.invariant.model_checksum == checkpoint.tensor_checksum


def test_auroc_style_quality_control_is_invariant_across_repeated_reads(tmp_path) -> None:
    _checkpoint, result = _scored_result(tmp_path)
    path = result.manifest.evaluation_records[0].path

    def mean_reconstruction_error() -> float:
        value = pl.read_parquet(path).get_column("reconstruction_error").mean()
        assert isinstance(value, int | float)
        return float(value)

    readings = [mean_reconstruction_error() for _ in range(3)]
    assert readings[0] == readings[1] == readings[2]
