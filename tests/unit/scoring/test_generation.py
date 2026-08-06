from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import AUTOENCODER, BATCH_SIZE, FEATURE_NAMES, benign_frame, client_identity
from tests.unit.scoring.helpers import selected_checkpoint

from datp_core.domain.enums import CheckpointStatus
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.scoring.federated import generate_federated_scores
from datp_core.pipeline.scoring.models import ClientScoringInput, ScoreGenerationRequest
from datp_core.runtime.compute import resolve_cuda_device


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


def _request(
    tmp_path: Path,
    checkpoint: CheckpointCandidate,
    *,
    clients: tuple[ClientScoringInput, ...] | None = None,
    preprocessing_state_set_checksum: Checksum | None = None,
) -> ScoreGenerationRequest:
    return ScoreGenerationRequest(
        checkpoint=checkpoint,
        scored_split_protocol=checkpoint.coordinate.split_protocol,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=_clients() if clients is None else clients,
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=(
            checkpoint.preprocessing_state_set_checksum
            if preprocessing_state_set_checksum is None
            else preprocessing_state_set_checksum
        ),
        split_manifest_checksum=checkpoint.split_manifest_checksum,
    )


def test_generate_federated_scores_writes_one_file_per_client_per_partition(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    result = generate_federated_scores(_request(tmp_path, checkpoint), resolve_cuda_device())
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
    with pytest.raises(ScientificContractError, match="non-test-selected checkpoint"):
        generate_federated_scores(_request(tmp_path, raw_candidate), resolve_cuda_device())


def test_generate_federated_scores_rejects_preprocessing_checksum_mismatch(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    request = _request(
        tmp_path,
        checkpoint,
        preprocessing_state_set_checksum=Checksum("f" * 64),
    )
    with pytest.raises(ScientificContractError, match="preprocessing checksum mismatch"):
        generate_federated_scores(request, resolve_cuda_device())


def test_generate_federated_scores_rejects_duplicate_clients(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    duplicated = (_clients()[0], _clients()[0])
    with pytest.raises(ScientificContractError, match="duplicate client identities"):
        generate_federated_scores(
            _request(tmp_path, checkpoint, clients=duplicated),
            resolve_cuda_device(),
        )


def test_score_reload_equality_detects_a_corrupted_file(tmp_path: Path) -> None:
    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    result = generate_federated_scores(_request(tmp_path, checkpoint), resolve_cuda_device())
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
    from datp_core.pipeline.scoring.frames import validate_persisted_score_frame

    with pytest.raises(ArtifactIntegrityError, match="checksum changed"):
        validate_persisted_score_frame(victim.path, victim.checksum, victim.row_count)


def test_scoring_rejects_attack_labelled_calibration_rows(tmp_path: Path) -> None:
    from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel

    checkpoint = selected_checkpoint(tmp_path / "checkpoint")
    attack_frame = benign_frame(RowCount(6), seed=Seed(1), label=PopulationOutcomeLabel.ATTACK.value)
    attack_client = ClientScoringInput(
        client=client_identity("client_a"),
        calibration_features=attack_frame,
        evaluation_features=benign_frame(RowCount(6), seed=Seed(2)),
    )
    with pytest.raises(LeakageError, match="benign calibration"):
        generate_federated_scores(
            _request(tmp_path, checkpoint, clients=(attack_client,)),
            resolve_cuda_device(),
        )
