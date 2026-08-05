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
