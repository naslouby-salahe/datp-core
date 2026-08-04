from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import AUTOENCODER, BATCH_SIZE, FEATURE_NAMES, benign_frame, client_identity
from tests.unit.scoring.helpers import selected_checkpoint

from datp_core.domain.enums import CheckpointStatus
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, RowCount, Seed
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import (
    ClientScoringInput,
    ScoreGenerationRequest,
    generate_federated_scores,
)


def _clients() -> tuple[ClientScoringInput, ...]:
    return (
        ClientScoringInput(
            client=client_identity("client_a"),
            calibration_features=benign_frame(RowCount(6), seed=Seed(1)),
            evaluation_features=benign_frame(RowCount(6), seed=Seed(2)),
        ),
        ClientScoringInput(
            client=client_identity("client_b"),
            calibration_features=benign_frame(RowCount(6), seed=Seed(3)),
            evaluation_features=benign_frame(RowCount(6), seed=Seed(4)),
        ),
    )


def test_generate_federated_scores_writes_one_file_per_client_per_partition(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=_clients(),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    result = generate_federated_scores(request, device)
    assert len(result.manifest.calibration_records) == 2
    assert len(result.manifest.evaluation_records) == 2
    for record in (*result.manifest.calibration_records, *result.manifest.evaluation_records):
        assert record.path.is_file()


def test_generate_federated_scores_rejects_a_raw_candidate_checkpoint(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    raw_candidate = checkpoint.__class__(
        coordinate=checkpoint.coordinate,
        round_number=checkpoint.round_number,
        client=checkpoint.client,
        tensor_path=checkpoint.tensor_path,
        tensor_checksum=checkpoint.tensor_checksum,
        mean_training_loss=checkpoint.mean_training_loss,
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    device = resolve_cuda_device()
    request = ScoreGenerationRequest(
        checkpoint=raw_candidate,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=_clients(),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=raw_candidate.preprocessing_state_set_checksum,
        split_manifest_checksum=raw_candidate.split_manifest_checksum,
    )
    with pytest.raises(ScientificContractError, match="non-test-selected checkpoint"):
        generate_federated_scores(request, device)


def test_generate_federated_scores_rejects_preprocessing_checksum_mismatch(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=_clients(),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=Checksum("f" * 64),
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    with pytest.raises(ScientificContractError, match="preprocessing checksum mismatch"):
        generate_federated_scores(request, device)


def test_generate_federated_scores_rejects_duplicate_clients(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    duplicated = (_clients()[0], _clients()[0])
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=duplicated,
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    with pytest.raises(ScientificContractError, match="duplicate client identities"):
        generate_federated_scores(request, device)


def test_score_reload_equality_detects_a_corrupted_file(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=_clients(),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    result = generate_federated_scores(request, device)
    victim = result.manifest.calibration_records[0]
    import polars as pl

    replacement = pl.DataFrame(
        {
            "stable_row_id": ["different"],
            "outcome_label": ["benign"],
            "reconstruction_error": [0.0],
        }
    )
    replacement.write_parquet(victim.path)
    from datp_core.pipeline.scoring.frame_contract import validate_persisted_score_frame

    with pytest.raises(ArtifactIntegrityError, match="checksum changed"):
        validate_persisted_score_frame(victim.path, victim.checksum, victim.row_count)


def test_scoring_rejects_attack_labelled_calibration_rows(tmp_path: Path) -> None:
    from datp_core.populations.models import PopulationOutcomeLabel

    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    device = resolve_cuda_device()
    attack_frame = benign_frame(RowCount(6), seed=Seed(1), label=PopulationOutcomeLabel.ATTACK.value)
    request = ScoreGenerationRequest(
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=(
            ClientScoringInput(
                client=client_identity("client_a"),
                calibration_features=attack_frame,
                evaluation_features=benign_frame(RowCount(6), seed=Seed(2)),
            ),
        ),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=checkpoint.preprocessing_state_set_checksum,
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )
    with pytest.raises(LeakageError, match="benign calibration"):
        generate_federated_scores(request, device)
