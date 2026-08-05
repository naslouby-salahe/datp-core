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
from datp_core.domain.values import ModelCoefficientValue, Seed
from datp_core.pipeline.federated_execution import bounded_evidence_seed_directory
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.layout import evaluation_run_directory, experiment_output_directory
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


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


def test_metrics_share_one_threshold_and_evaluation_run() -> None:
    root = Path("outputs")
    primary = coordinate()
    control = replace(primary, metric=MetricId.MEAN_FPR)

    assert evaluation_run_directory(root, primary) == evaluation_run_directory(root, control)
    assert experiment_output_directory(root, primary) != experiment_output_directory(root, control)


def test_threshold_methods_keep_distinct_evaluation_runs() -> None:
    root = Path("outputs")
    shared = coordinate()
    local = replace(shared, threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD)

    assert evaluation_run_directory(root, shared) != evaluation_run_directory(root, local)


def test_every_non_metric_coordinate_dimension_changes_the_run_identity() -> None:
    root = Path("outputs")
    primary = coordinate()
    alternatives = (
        replace(primary, experiment=ExperimentId.HISTORICAL_DATP_REPRODUCTION),
        replace(primary, evidence_role=EvidenceRole.ANCHOR_REPRODUCTION),
        replace(primary, dataset=DatasetId.EDGE_IIOTSET),
        replace(primary, population=PopulationId.EDGE_SENSOR_GROUPS),
        replace(
            primary,
            training_model=TrainingModelId.FEDPROX_AUTOENCODER,
            model_coefficient=ModelCoefficientValue(0.1),
        ),
        replace(primary, training_seed=Seed(1)),
        replace(primary, split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE),
        replace(primary, preprocessing_protocol=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX),
        replace(primary, threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD),
    )

    primary_path = evaluation_run_directory(root, primary)
    assert all(evaluation_run_directory(root, alternative) != primary_path for alternative in alternatives)


def test_bounded_evidence_paths_separate_external_and_temporal_claims() -> None:
    root = Path("outputs")
    seed = Seed(0)
    external = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        temporal_state=None,
    )
    frozen = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.FROZEN_FUTURE,
    )
    recalibrated = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.RECALIBRATED_FUTURE,
    )

    paths = {
        bounded_evidence_seed_directory(identity, seed, root)
        for identity in (external, frozen, recalibrated)
    }
    assert len(paths) == 3
    assert all(path.is_relative_to(root) for path in paths)
