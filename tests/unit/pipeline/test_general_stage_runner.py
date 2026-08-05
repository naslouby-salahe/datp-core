from dataclasses import replace
from pathlib import Path

from datp_core.domain.enums import (
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
from datp_core.domain.values import ByteCount, Checksum, ModelCoefficientValue, Seed, checksum_bytes
from datp_core.pipeline.campaign import GeneralExperimentOutputStore, GeneralStageRunner
from datp_core.pipeline.execution import ExecutionProvenance, ExistingExperimentState, PipelineStage, StageOutcome
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.completion import build_completion_record, write_completion_record
from datp_core.pipeline.publication.layout import experiment_output_directory
from datp_core.pipeline.publication.records import ArtifactKind, ArtifactRecord, ArtifactState
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS


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
    runner = GeneralStageRunner()
    result = runner.run(PipelineStage.PREFLIGHT, coordinate(), provenance())
    assert result.outcome is StageOutcome.COMPLETED
    assert coordinate().stable_key in result.evidence


def test_temporal_coordinates_are_blocked_from_single_coordinate_stages() -> None:
    runner = GeneralStageRunner()
    temporal_coordinate = replace(coordinate(), temporal_state=TemporalState.FROZEN_FUTURE)
    result = runner.run(PipelineStage.CONSTRUCT_POPULATION, temporal_coordinate, provenance())
    assert result.outcome is StageOutcome.BLOCKED
    assert "run_temporal_future_pair" in result.evidence


def test_ditto_training_model_is_blocked_rather_than_approximated() -> None:
    runner = GeneralStageRunner()
    ditto_coordinate = replace(
        coordinate(),
        training_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=ModelCoefficientValue(DITTO_TRAINING_PROTOCOLS[0].regularization.value),
    )
    result = runner.run(PipelineStage.TRAIN_DETECTOR, ditto_coordinate, provenance())
    assert result.outcome is StageOutcome.BLOCKED
    assert "not single-coordinate" in result.evidence


def test_ciciot2023_dataset_is_blocked_for_undeclared_autoencoder() -> None:
    runner = GeneralStageRunner()
    cic_coordinate = replace(coordinate(), dataset=DatasetId.CICIOT2023)
    result = runner.run(PipelineStage.TRAIN_DETECTOR, cic_coordinate, provenance())
    assert result.outcome is StageOutcome.BLOCKED
    assert "CICIOT2023" in result.evidence


def test_publish_report_is_rejected_as_a_per_coordinate_stage() -> None:
    runner = GeneralStageRunner()
    result = runner.run(PipelineStage.PUBLISH_REPORT, coordinate(), provenance())
    assert result.outcome is StageOutcome.BLOCKED
    assert "campaign-level" in result.evidence


def test_verify_anchor_rejects_experiments_other_than_the_historical_reproduction() -> None:
    runner = GeneralStageRunner()
    result = runner.run(PipelineStage.VERIFY_ANCHOR, coordinate(), provenance())
    assert result.outcome is StageOutcome.BLOCKED
    assert "historical reproduction" in result.evidence


def test_output_store_reports_absent_for_missing_directory(tmp_path: Path) -> None:
    store = GeneralExperimentOutputStore()
    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.ABSENT


def test_output_store_reports_incomplete_for_directory_without_completion_record(tmp_path: Path) -> None:
    store = GeneralExperimentOutputStore()
    directory = experiment_output_directory(tmp_path, coordinate())
    directory.mkdir(parents=True)
    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.INCOMPLETE


def test_output_store_round_trips_a_valid_completion_record(tmp_path: Path) -> None:
    store = GeneralExperimentOutputStore()
    directory = experiment_output_directory(tmp_path, coordinate())
    relative = directory.relative_to(tmp_path) / "result.json"
    (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    payload = b"{}"
    (tmp_path / relative).write_bytes(payload)
    artifact = ArtifactRecord(
        kind=ArtifactKind.SUMMARY,
        relative_path=relative,
        checksum=checksum_bytes(payload),
        byte_count=ByteCount(len(payload)),
        state=ArtifactState.PUBLISHED,
    )
    record = build_completion_record(plan_digest="plan", campaign_digest="campaign", artifacts=(artifact,))
    write_completion_record(directory, record)

    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.COMPLETE_VALID

    store.delete(coordinate(), tmp_path)
    assert store.state(coordinate(), tmp_path) is ExistingExperimentState.ABSENT
