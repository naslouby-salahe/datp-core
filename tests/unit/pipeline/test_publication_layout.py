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
    TrainingModelId,
)
from datp_core.domain.values import Seed
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.layout import evaluation_run_directory, experiment_output_directory


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
        replace(primary, training_model=TrainingModelId.FEDPROX_AUTOENCODER, model_coefficient=0.1),
        replace(primary, training_seed=Seed(1)),
        replace(primary, split_protocol=SplitProtocolId.TEMPORAL_55_15_10_20),
        replace(primary, preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_MIN_MAX),
        replace(primary, threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD),
    )

    primary_path = evaluation_run_directory(root, primary)
    assert all(evaluation_run_directory(root, alternative) != primary_path for alternative in alternatives)
