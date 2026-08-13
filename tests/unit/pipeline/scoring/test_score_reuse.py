from pathlib import Path

import polars as pl
import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    FEATURE_NAMES,
    FEDAVG_PROTOCOL,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    benign_frame,
    build_all_client_inputs,
    client_identity,
    fedavg_coordinate,
    require_cuda,
)

from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.numeric import RoundNumber, RowCount, Seed
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.checkpoints.publication import write_federated_training
from datp_core.detector.scoring import federated as scoring_federated
from datp_core.detector.scoring.models import ClientScoringInput, GenerateFederatedScoresRequest
from datp_core.detector.training.contracts import FederatedClientDataResidency
from datp_core.detector.training.engine import (
    FederatedTrainingExecution,
    FederatedTrainingRequest,
    run_federated_training,
)
from datp_core.detector.training.models import FederatedTrainingResult

FAST_PROTOCOL = DiagnosticSnapshotProtocol(diagnostic_rounds=(), maximum_round=RoundNumber(1))
CLIENT_IDS = ("client_a", "client_b")


def _trained_result(tmp_path: Path):
    request = FederatedTrainingRequest(
        coordinate=fedavg_coordinate(Seed(0)),
        clients=build_all_client_inputs(tmp_path),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        diagnostic_snapshot_protocol=FAST_PROTOCOL,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        output_directory=tmp_path / "training",
        client_data_residency=FederatedClientDataResidency.STREAMING,
    )
    execution = run_federated_training(request)
    return write_federated_training(
        FederatedTrainingExecution(training_result=execution.training_result), tmp_path / "training"
    )


def _client_scoring_inputs() -> tuple[ClientScoringInput, ...]:
    return tuple(
        ClientScoringInput(
            client=client_identity(client_id),
            calibration_features=benign_frame(RowCount(4), seed=Seed(index * 2)),
            evaluation_features=benign_frame(RowCount(4), seed=Seed(index * 2 + 1)),
        )
        for index, client_id in enumerate(CLIENT_IDS)
    )


def _request(tmp_path: Path, training) -> GenerateFederatedScoresRequest:
    return GenerateFederatedScoresRequest(
        training=training,
        scored_split_protocol=training.coordinate.split_protocol,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=_client_scoring_inputs(),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        overwrite=False,
    )


def test_publish_federated_scores_reuses_persisted_evidence_across_separate_invocations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    require_cuda()
    training = _trained_result(tmp_path)

    first = scoring_federated.publish_federated_scores(_request(tmp_path, training))

    def _fail_if_regenerated(request: GenerateFederatedScoresRequest, device: object) -> None:
        pytest.fail("score coordinate already has valid persisted evidence and must not regenerate")

    monkeypatch.setattr(scoring_federated, "_generate_federated_scores", _fail_if_regenerated)

    second = scoring_federated.publish_federated_scores(_request(tmp_path, training))

    assert second.manifest.calibration_records == first.manifest.calibration_records
    assert second.manifest.evaluation_records == first.manifest.evaluation_records


def test_publish_federated_scores_raises_explicitly_when_row_identities_diverge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    require_cuda()
    training = _trained_result(tmp_path)
    scoring_federated.publish_federated_scores(_request(tmp_path, training))

    diverged_request = _request(tmp_path, training)
    relabelled_client = ClientScoringInput(
        client=diverged_request.clients[0].client,
        calibration_features=benign_frame(RowCount(4), seed=Seed(999)),
        evaluation_features=diverged_request.clients[0].evaluation_features,
    )
    diverged_request.clients = (relabelled_client, diverged_request.clients[1])

    def _fail_if_regenerated(request: GenerateFederatedScoresRequest, device: object) -> None:
        pytest.fail("row-identity divergence must fail explicitly rather than trigger a silent regeneration")

    monkeypatch.setattr(scoring_federated, "_generate_federated_scores", _fail_if_regenerated)

    with pytest.raises(ArtifactIntegrityError):
        scoring_federated.publish_federated_scores(diverged_request)


def test_load_federated_scores_returns_none_without_any_persisted_artifact(tmp_path: Path) -> None:
    training = _trained_result(tmp_path)

    result = scoring_federated.load_federated_scores(_request(tmp_path, training))

    assert result is None


def test_load_federated_scores_raises_on_incomplete_persisted_evidence(tmp_path: Path) -> None:
    require_cuda()
    training = _trained_result(tmp_path)
    request = _request(tmp_path, training)
    scoring_federated.publish_federated_scores(request)

    (request.output_directory / CLIENT_IDS[0] / "calibration.parquet").unlink()

    with pytest.raises(ArtifactIntegrityError):
        scoring_federated.load_federated_scores(_request(tmp_path, training))


def test_load_federated_scores_rejects_cached_label_provenance_drift(tmp_path: Path) -> None:
    require_cuda()
    training = _trained_result(tmp_path)
    request = _request(tmp_path, training)
    scoring_federated.publish_federated_scores(request)

    path = request.output_directory / CLIENT_IDS[0] / "evaluation.parquet"
    pl.read_parquet(path).with_columns(pl.lit("tampered").alias("outcome_label")).write_parquet(path)

    with pytest.raises(ArtifactIntegrityError, match="source provenance"):
        scoring_federated.load_federated_scores(_request(tmp_path, training))


def test_publish_federated_scores_rejects_reuse_for_a_different_terminal_detector(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    require_cuda()
    training = _trained_result(tmp_path)
    scoring_federated.publish_federated_scores(_request(tmp_path, training))
    changed_state = training.terminal_model_state.to_torch_state_dict()
    changed_state[next(iter(changed_state))].add_(1.0)
    altered_training = FederatedTrainingResult(
        coordinate=training.coordinate,
        autoencoder=training.autoencoder,
        diagnostic_snapshot_protocol=training.diagnostic_snapshot_protocol,
        history=training.history,
        termination_reason=training.termination_reason,
        terminal_model_state=training.terminal_model_state.from_torch_state_dict(changed_state),
        device_name=training.device_name,
        batch_size_used=training.batch_size_used,
    )

    monkeypatch.setattr(
        scoring_federated,
        "_generate_federated_scores",
        lambda _request, _device: pytest.fail("stale score artifacts must not be regenerated implicitly"),
    )

    with pytest.raises(ArtifactIntegrityError, match="terminal detector"):
        scoring_federated.publish_federated_scores(_request(tmp_path, altered_training))
