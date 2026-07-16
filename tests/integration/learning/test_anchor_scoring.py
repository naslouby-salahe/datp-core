from pathlib import Path

import pytest
import torch
from torch import Tensor, nn

from datp_core.application.ports.scoring import GenerateCalibrationScoresRequest, GenerateTestScoresRequest
from datp_core.domain.artifacts.keys import SerializationFormat, StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.lineage import (
    DatasetSourceIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    PartitionIdentity,
    SplitIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.errors import ScoringError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, CheckpointProtocol
from datp_core.domain.learning.scores import ScoreGenerationSpec, ScoringBatchSpec
from datp_core.domain.learning.training import PrecisionMode
from datp_core.domain.runtime.admissibility import BatchSize
from datp_core.domain.runtime.seeds import RoundNumber, Seed
from datp_core.infrastructure.persistence.bundles import FileArtifactBundleStore
from datp_core.infrastructure.persistence.roots import bind_storage_root
from datp_core.infrastructure.scoring.anchor import (
    AnchorCalibrationScoreGenerationWorkflow,
    AnchorTestScoreGenerationWorkflow,
    score_client_batch,
)


class _IdentityModel(nn.Module):
    def forward(self, values: Tensor) -> Tensor:
        return values.clone()


class _OffsetModel(nn.Module):
    def forward(self, values: Tensor) -> Tensor:
        return values + 1.0


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _checkpoint(character: str) -> CheckpointDescriptor:
    artifact_ref = ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.TORCH_STATE,
    )
    return CheckpointDescriptor(
        checkpoint_id=CheckpointId(value=f"checkpoint-{character * 64}"),
        round=RoundNumber(value=118),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=_fingerprint("a")),
        protocol=CheckpointProtocol.ANCHOR_TERMINATION,
        artifact_ref=artifact_ref,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )


def _processed_splits() -> ProcessedSplitResult:
    return ProcessedSplitResult(
        artifacts=(
            ArtifactRef(
                artifact_id=ArtifactId(value="artifact-" + "b" * 64),
                artifact_type=ArtifactType.PROCESSED_SPLIT,
                content_hash="b" * 64,
                schema_version=ArtifactSchemaVersion(value="v1"),
                serialization_format=SerializationFormat.PARQUET,
            ),
        ),
        split_manifest_identity=SplitIdentity(value=_fingerprint("c")),
        preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("d")),
        source_row_lineage=(DatasetSourceIdentity(value=_fingerprint("e")),),
    )


def _scoring_spec(*, batch_size: int = 4) -> ScoreGenerationSpec:
    return ScoreGenerationSpec(
        scoring_batch=ScoringBatchSpec(
            calibration_batch_size=BatchSize(value=batch_size),
            test_batch_size=BatchSize(value=batch_size),
            temporal_batch_size=BatchSize(value=batch_size),
        ),
        precision=PrecisionMode.FP32,
        numeric_equivalence_policy="anchor_batched_vs_reference_v1",
    )


def _calibration_workflow(
    *, model: nn.Module, batches: dict[ClientId, Tensor]
) -> AnchorCalibrationScoreGenerationWorkflow:
    return AnchorCalibrationScoreGenerationWorkflow(
        model=model,
        device=torch.device("cpu"),
        dataset_source_identity=DatasetSourceIdentity(value=_fingerprint("e")),
        partition_identity=PartitionIdentity(value=_fingerprint("f")),
        feature_schema_identity=FeatureSchemaIdentity(value=_fingerprint("0")),
        calibration_batches=batches,
    )


def test_batched_scoring_matches_a_single_pass_reference() -> None:
    values = torch.arange(24, dtype=torch.float32).reshape(6, 4)

    batched = score_client_batch(model=_OffsetModel(), device=torch.device("cpu"), batch=values, batch_size=2)
    reference = torch.mean(torch.square((values + 1.0) - values), dim=1)

    assert torch.equal(batched, reference)


def test_calibration_workflow_rejects_empty_client_batches() -> None:
    workflow = _calibration_workflow(model=_IdentityModel(), batches={})
    request = GenerateCalibrationScoresRequest(
        processed_splits=_processed_splits(), checkpoint=_checkpoint("1"), scoring=_scoring_spec()
    )

    with pytest.raises(ScoringError):
        workflow.generate(request)


def test_calibration_workflow_produces_zero_reconstruction_scores_for_an_identity_model() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    batches = {
        client_a: torch.rand(5, 3, dtype=torch.float32),
        client_b: torch.rand(3, 3, dtype=torch.float32),
    }
    workflow = _calibration_workflow(model=_IdentityModel(), batches=batches)
    request = GenerateCalibrationScoresRequest(
        processed_splits=_processed_splits(), checkpoint=_checkpoint("2"), scoring=_scoring_spec()
    )

    result = workflow.generate(request)

    entries = result.scores.per_client.values.entries
    assert tuple(entry.client_id for entry in entries) == (client_a, client_b)
    for entry in entries:
        assert entry.value.sample_count.value == batches[entry.client_id].shape[0]
    assert result.scores.lineage.context.roster.client_ids == (client_a, client_b)


def _bundle_store(path: Path) -> FileArtifactBundleStore:
    return FileArtifactBundleStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
            absolute_path=path,
        )
    )


def _test_workflow(
    *, model: nn.Module, benign: dict[ClientId, Tensor], attack: dict[ClientId, Tensor], path: Path
) -> AnchorTestScoreGenerationWorkflow:
    return AnchorTestScoreGenerationWorkflow(
        model=model,
        device=torch.device("cpu"),
        dataset_source_identity=DatasetSourceIdentity(value=_fingerprint("e")),
        partition_identity=PartitionIdentity(value=_fingerprint("f")),
        feature_schema_identity=FeatureSchemaIdentity(value=_fingerprint("0")),
        benign_batches=benign,
        attack_batches=attack,
        bundle_committer=_bundle_store(path),
        stage_identity=_fingerprint("9"),
    )


def test_test_workflow_rejects_a_mismatched_benign_attack_roster(tmp_path: Path) -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    benign = {client_a: torch.rand(4, 3)}
    attack = {client_b: torch.rand(2, 3)}
    model = _IdentityModel()

    with pytest.raises(ScoringError):
        _test_workflow(model=model, benign=benign, attack=attack, path=tmp_path)


def test_test_workflow_commits_the_atomic_benign_attack_pair(tmp_path: Path) -> None:
    client_a = ClientId(value="client-a")
    benign = {client_a: torch.rand(6, 3, dtype=torch.float32)}
    attack = {client_a: torch.rand(4, 3, dtype=torch.float32)}
    workflow = _test_workflow(model=_IdentityModel(), benign=benign, attack=attack, path=tmp_path)
    request = GenerateTestScoresRequest(
        processed_splits=_processed_splits(), checkpoint=_checkpoint("3"), scoring=_scoring_spec()
    )

    result = workflow.generate(request)

    entries = result.scores.per_client.values.entries
    assert len(entries) == 1
    artifact = entries[0].value
    assert artifact.benign_sample_count.value == 6
    assert artifact.attack_sample_count.value == 4
    bundle_directories = tuple((tmp_path / ".artifact-bundles").iterdir())
    assert len(bundle_directories) == 1
    assert (bundle_directories[0] / "commit-marker.json").is_file()
    assert (bundle_directories[0] / "benign").is_file()
    assert (bundle_directories[0] / "attack").is_file()
