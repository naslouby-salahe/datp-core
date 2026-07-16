import pytest
import torch
from torch import Tensor, nn

from datp_core.domain.artifacts.lineage import CentralizedCheckpointIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.errors import ScoringError
from datp_core.domain.experiments.identities import ClientId
from datp_core.infrastructure.learning.centralized.nbaiot_b0_scoring import (
    B0CalibrationScoreGenerationWorkflow,
    B0TestScoreGenerationWorkflow,
)


class _IdentityModel(nn.Module):
    def forward(self, values: Tensor) -> Tensor:
        return values.clone()


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _checkpoint_identity() -> CentralizedCheckpointIdentity:
    return CentralizedCheckpointIdentity(value=_fingerprint("1"))


def _calibration_workflow(*, batches: dict[ClientId, Tensor]) -> B0CalibrationScoreGenerationWorkflow:
    return B0CalibrationScoreGenerationWorkflow(
        model=_IdentityModel(),
        device=torch.device("cpu"),
        centralized_checkpoint_identity=_checkpoint_identity(),
        centralized_checkpoint_content_hash="2" * 64,
        calibration_split_identity=SplitIdentity(value=_fingerprint("3")),
        calibration_batches=batches,
    )


def test_calibration_workflow_rejects_empty_client_batches() -> None:
    workflow = _calibration_workflow(batches={})

    with pytest.raises(ScoringError):
        workflow.generate(batch_size=4)


def test_calibration_workflow_produces_one_artifact_per_client_in_canonical_order() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    batches = {
        client_b: torch.rand(4, 3, dtype=torch.float32),
        client_a: torch.rand(6, 3, dtype=torch.float32),
    }
    workflow = _calibration_workflow(batches=batches)

    artifacts = workflow.generate(batch_size=4)

    assert tuple(artifact.client_id for artifact in artifacts) == (client_a, client_b)
    for artifact in artifacts:
        assert artifact.sample_count.value == batches[artifact.client_id].shape[0]
        assert artifact.centralized_checkpoint_identity == _checkpoint_identity()


def _test_workflow(*, benign: dict[ClientId, Tensor], attack: dict[ClientId, Tensor]) -> B0TestScoreGenerationWorkflow:
    return B0TestScoreGenerationWorkflow(
        model=_IdentityModel(),
        device=torch.device("cpu"),
        centralized_checkpoint_identity=_checkpoint_identity(),
        centralized_checkpoint_content_hash="2" * 64,
        test_split_identity=SplitIdentity(value=_fingerprint("4")),
        benign_batches=benign,
        attack_batches=attack,
    )


def test_test_workflow_rejects_a_mismatched_benign_attack_roster() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    benign = {client_a: torch.rand(4, 3)}
    attack = {client_b: torch.rand(2, 3)}

    with pytest.raises(ScoringError):
        _test_workflow(benign=benign, attack=attack)


def test_test_workflow_produces_a_benign_attack_pair_per_client() -> None:
    client_a = ClientId(value="client-a")
    benign = {client_a: torch.rand(6, 3, dtype=torch.float32)}
    attack = {client_a: torch.rand(4, 3, dtype=torch.float32)}
    workflow = _test_workflow(benign=benign, attack=attack)

    artifacts = workflow.generate(batch_size=4)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.benign_sample_count.value == 6
    assert artifact.attack_sample_count.value == 4
    assert artifact.centralized_checkpoint_identity == _checkpoint_identity()
