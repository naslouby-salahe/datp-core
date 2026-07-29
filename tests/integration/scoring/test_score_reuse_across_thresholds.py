from pathlib import Path

import polars as pl
import pytest
from tests.unit.learning.federated.helpers import AUTOENCODER, BATCH_SIZE, FEATURE_NAMES, benign_frame, client_identity
from tests.unit.scoring.helpers import selected_checkpoint

from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import (
    ClientScoringInput,
    ScoreGenerationRequest,
    generate_federated_scores,
    reject_score_regeneration_per_threshold,
    reject_threshold_identity_in_score_coordinate,
)


def _mean_reconstruction_error(path: Path) -> float:
    frame = pl.read_parquet(path)
    mean_value = frame.get_column("reconstruction_error").mean()
    assert isinstance(mean_value, int | float)
    return float(mean_value)


def test_one_score_artifact_is_reusable_across_every_simulated_threshold_method(tmp_path: Path) -> None:
    """A frozen score artifact must yield identical values no matter how many
    distinct threshold methods read it — generation happens exactly once."""
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    clients = (
        ClientScoringInput(
            client=client_identity("client_a"),
            calibration_features=benign_frame(8, seed=1),
            evaluation_features=benign_frame(8, seed=2),
        ),
    )
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=clients,
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    result = generate_federated_scores(request, device)
    calibration_path = result.manifest.calibration_records[0].path

    simulated_threshold_methods = (
        "shared_threshold",
        "local_threshold",
        "cluster_threshold",
        "local_conformal_threshold",
    )
    observed_means = {method: _mean_reconstruction_error(calibration_path) for method in simulated_threshold_methods}
    assert len(set(observed_means.values())) == 1

    for method in simulated_threshold_methods:
        with pytest.raises(ScientificContractError, match="threshold identity"):
            reject_threshold_identity_in_score_coordinate(method)
    reject_threshold_identity_in_score_coordinate(None)


def test_score_regeneration_per_threshold_is_structurally_forbidden() -> None:
    with pytest.raises(LeakageError, match="frozen detector outputs"):
        reject_score_regeneration_per_threshold()


def test_auroc_style_separability_over_the_same_score_artifact_is_invariant_across_reads(tmp_path: Path) -> None:
    """A quality control statistic computed over one frozen score artifact must not
    change depending on which threshold-method context reads it."""
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    clients = (
        ClientScoringInput(
            client=client_identity("client_a"),
            calibration_features=benign_frame(8, seed=1),
            evaluation_features=benign_frame(8, seed=2),
        ),
    )
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=clients,
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    result = generate_federated_scores(request, device)
    evaluation_path = result.manifest.evaluation_records[0].path

    def quality_control_statistic() -> float:
        return _mean_reconstruction_error(evaluation_path)

    readings = [quality_control_statistic() for _ in range(3)]
    assert readings[0] == readings[1] == readings[2]
