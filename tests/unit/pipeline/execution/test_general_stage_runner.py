from dataclasses import replace
from pathlib import Path

import pytest

import datp_core.experiments.execution.workspace as workspace_module
from datp_core.artifacts.layout import experiment_output_directory
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.models import ArtifactKind, ArtifactRecord, ArtifactState
from datp_core.artifacts.repositories.publication import build_completion_record, write_completion_record
from datp_core.core.identifiers import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.core.numeric import ByteCount, ModelCoefficientValue, Seed
from datp_core.detector.training.protocols import DITTO_TRAINING_PROTOCOLS
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.execution.engine import CompletionRecordOutputStore, PipelineStageRunner
from datp_core.experiments.execution.models import (
    ExecutionProvenance,
    ExistingExperimentState,
    PipelineStage,
    StageOutcome,
)

OUTPUT_ROOT = Path("outputs")


def coordinate() -> ExperimentCoordinate:
    return ExperimentCoordinate(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        evidence_role=EvidenceRole.CONFIRMATORY,
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        training_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model_coefficient=None,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        temporal_state=None,
    )


def provenance() -> ExecutionProvenance:
    return ExecutionProvenance(
        plan_digest=Checksum("plan"),
        campaign_digest=Checksum("campaign"),
        protocol_digest=Checksum("protocol"),
    )


def test_preflight_completes_without_touching_disk() -> None:
    runner = PipelineStageRunner()
    result = runner.run(PipelineStage.PREFLIGHT, coordinate(), provenance(), OUTPUT_ROOT)
    assert result.outcome is StageOutcome.COMPLETED
    assert coordinate().stable_key in result.evidence


def test_context_resolved_once_across_metric_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Coordinates sharing a training coordinate reuse one resolved context.

    The federated execution context depends on the training coordinate, not the
    threshold method or metric, so a campaign resolves it once per training group.
    """
    runner = PipelineStageRunner()
    auroc_coordinate = replace(coordinate(), metric=MetricId.AUROC)
    other_seed_coordinate = replace(coordinate(), training_seed=Seed(1))

    resolved: list[str] = []

    def fake_resolve(coordinate: ExperimentCoordinate, _output_root: Path) -> object:
        resolved.append(coordinate.stable_key)
        return object()

    monkeypatch.setattr(workspace_module, "resolve_execution_context", fake_resolve)

    first = runner._workspace_for(coordinate(), OUTPUT_ROOT)
    second = runner._workspace_for(auroc_coordinate, OUTPUT_ROOT)
    third = runner._workspace_for(other_seed_coordinate, OUTPUT_ROOT)

    assert first.context is second.context
    assert first.context is not third.context
    assert len(resolved) == 2


def test_evaluation_resolved_once_across_metric_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Coordinates sharing a run directory reuse one evaluation result.

    The federated evaluation document is metric-independent, so a campaign
    evaluates once per metric-free run directory and reuses the result across
    metric coordinates. Changing the threshold method resolves anew.
    """
    runner = PipelineStageRunner()
    auroc_coordinate = replace(coordinate(), metric=MetricId.AUROC)
    local_coordinate = replace(
        coordinate(), metric=MetricId.AUROC, threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD
    )

    evaluated: list[str] = []

    def fake_evaluate(self: workspace_module.ExperimentWorkspace) -> object:
        evaluated.append(self.run_directory().as_posix())
        return object()

    monkeypatch.setattr(workspace_module.ExperimentWorkspace, "_evaluate", fake_evaluate)

    first = runner._workspace_for(coordinate(), OUTPUT_ROOT)
    second = runner._workspace_for(auroc_coordinate, OUTPUT_ROOT)
    third = runner._workspace_for(local_coordinate, OUTPUT_ROOT)

    assert first.evaluation is second.evaluation
    assert first.evaluation is not third.evaluation
    assert len(evaluated) == 2


def test_temporal_coordinates_are_blocked_from_single_coordinate_stages() -> None:
    runner = PipelineStageRunner()
    temporal_coordinate = replace(coordinate(), temporal_state=TemporalState.FROZEN_FUTURE)
    result = runner.run(PipelineStage.CONSTRUCT_POPULATION, temporal_coordinate, provenance(), OUTPUT_ROOT)
    assert result.outcome is StageOutcome.BLOCKED
    assert "paired temporal execution route" in result.evidence


def test_ditto_training_model_is_blocked_rather_than_approximated() -> None:
    runner = PipelineStageRunner()
    ditto_coordinate = replace(
        coordinate(),
        training_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=ModelCoefficientValue(DITTO_TRAINING_PROTOCOLS[0].regularization.value),
    )
    result = runner.run(PipelineStage.TRAIN_DETECTOR, ditto_coordinate, provenance(), OUTPUT_ROOT)
    assert result.outcome is StageOutcome.BLOCKED
    assert "global and personalized execution route" in result.evidence


def test_ciciot2023_dataset_is_blocked_for_undeclared_autoencoder() -> None:
    runner = PipelineStageRunner()
    cic_coordinate = replace(coordinate(), dataset=DatasetId.CICIOT2023)
    result = runner.run(PipelineStage.TRAIN_DETECTOR, cic_coordinate, provenance(), OUTPUT_ROOT)
    assert result.outcome is StageOutcome.BLOCKED
    assert "CICIOT2023" in result.evidence


def test_output_store_reports_absent_for_missing_directory(tmp_path: Path) -> None:
    store = CompletionRecordOutputStore()
    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.ABSENT


def test_output_store_reports_incomplete_for_directory_without_completion_record(tmp_path: Path) -> None:
    store = CompletionRecordOutputStore()
    directory = experiment_output_directory(tmp_path, coordinate())
    directory.mkdir(parents=True)
    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.INCOMPLETE


def test_output_store_round_trips_a_valid_completion_record(tmp_path: Path) -> None:
    store = CompletionRecordOutputStore()
    directory = experiment_output_directory(tmp_path, coordinate())
    relative = directory.relative_to(tmp_path) / "result.json"
    (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    payload = b"{}"
    (tmp_path / relative).write_bytes(payload)
    artifact = ArtifactRecord(
        kind=ArtifactKind.SUMMARY,
        relative_path=relative,
        checksum=Checksum.from_bytes(payload),
        byte_count=ByteCount(len(payload)),
        state=ArtifactState.PUBLISHED,
    )
    record = build_completion_record(
        plan_digest=provenance().plan_digest,
        campaign_digest=provenance().campaign_digest,
        protocol_digest=provenance().protocol_digest,
        artifacts=(artifact,),
    )
    write_completion_record(directory, record)

    assert store.state(coordinate(), tmp_path, provenance()) is ExistingExperimentState.COMPLETE_VALID

    store.delete(coordinate(), tmp_path)
    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.ABSENT


def test_output_store_detects_protocol_digest_mismatch_on_resume(tmp_path: Path) -> None:
    store = CompletionRecordOutputStore()
    directory = experiment_output_directory(tmp_path, coordinate())
    relative = directory.relative_to(tmp_path) / "result.json"
    (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    payload = b"{}"
    (tmp_path / relative).write_bytes(payload)
    artifact = ArtifactRecord(
        kind=ArtifactKind.SUMMARY,
        relative_path=relative,
        checksum=Checksum.from_bytes(payload),
        byte_count=ByteCount(len(payload)),
        state=ArtifactState.PUBLISHED,
    )
    record = build_completion_record(
        plan_digest=provenance().plan_digest,
        campaign_digest=provenance().campaign_digest,
        protocol_digest=provenance().protocol_digest,
        artifacts=(artifact,),
    )
    write_completion_record(directory, record)

    changed_protocol = replace(provenance(), protocol_digest=Checksum("different-protocol"))
    assert store.state(coordinate(), tmp_path, changed_protocol) is ExistingExperimentState.COMPLETE_INVALID
