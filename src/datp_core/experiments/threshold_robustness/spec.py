"""Threshold-estimation robustness and variant experiment specifications."""

from datp_core.analysis.metrics.contracts import ATTACK_QUALITY_CONTROL_METRICS, OPERATING_POINT_METRICS
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    TrainingModelId,
)
from datp_core.experiments.common.coordinates import ExperimentSpec

_THRESHOLD_METRICS = OPERATING_POINT_METRICS + ATTACK_QUALITY_CONTROL_METRICS

SHARED_CONSTRUCTION_SENSITIVITY = ExperimentSpec(
    id=ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
    role=EvidenceRole.THRESHOLD_VARIANT,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    ),
    metrics=_THRESHOLD_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
QUANTILE_SENSITIVITY = ExperimentSpec(
    id=ExperimentId.QUANTILE_SENSITIVITY,
    role=EvidenceRole.THRESHOLD_VARIANT,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=_THRESHOLD_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
CALIBRATION_SIZE_ABLATION = ExperimentSpec(
    id=ExperimentId.CALIBRATION_SIZE_ABLATION,
    role=EvidenceRole.THRESHOLD_VARIANT,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.LOCAL_THRESHOLD,),
    metrics=_THRESHOLD_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
FIXED_SHRINKAGE_CURVE = ExperimentSpec(
    id=ExperimentId.FIXED_SHRINKAGE_CURVE,
    role=EvidenceRole.THRESHOLD_VARIANT,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,),
    metrics=_THRESHOLD_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
SIZE_AWARE_SHRINKAGE = ExperimentSpec(
    id=ExperimentId.SIZE_AWARE_SHRINKAGE,
    role=EvidenceRole.THRESHOLD_VARIANT,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,),
    metrics=_THRESHOLD_METRICS,
    readiness=ExperimentReadiness.INFEASIBLE,
)
LOCAL_CONFORMAL_COVERAGE = ExperimentSpec(
    id=ExperimentId.LOCAL_CONFORMAL_COVERAGE,
    role=EvidenceRole.THRESHOLD_VARIANT,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,),
    metrics=(MetricId.TARGET_COVERAGE, MetricId.ACHIEVED_COVERAGE, MetricId.ABSOLUTE_COVERAGE_ERROR),
    readiness=ExperimentReadiness.DECLARED,
)
GROUP_MEDIAN_SUPPLEMENT = ExperimentSpec(
    id=ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
    role=EvidenceRole.EXPLORATORY,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.CLUSTER_THRESHOLD,),
    metrics=_THRESHOLD_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)

THRESHOLD_ROBUSTNESS_EXPERIMENTS = (
    SHARED_CONSTRUCTION_SENSITIVITY,
    QUANTILE_SENSITIVITY,
    CALIBRATION_SIZE_ABLATION,
    FIXED_SHRINKAGE_CURVE,
    SIZE_AWARE_SHRINKAGE,
    LOCAL_CONFORMAL_COVERAGE,
    GROUP_MEDIAN_SUPPLEMENT,
)
