from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.errors import DomainValidationError


class MetricFamily(StrEnum):
    OPERATING_POINT = "operating_point"
    DETECTION_QUALITY = "detection_quality"
    EQUITY = "equity"
    ESTIMATION = "estimation"
    CLUSTER = "cluster"
    DISTRIBUTION = "distribution"
    DIAGNOSTIC = "diagnostic"
    RESOURCE = "resource"


class OperatingPointMetric(StrEnum):
    FPR = "fpr"
    TPR = "tpr"
    CV_FPR = "cv_fpr"
    CV_TPR = "cv_tpr"
    IQR_FPR = "iqr_fpr"
    FPR_RANGE = "fpr_range"
    WORST_CLIENT_FPR = "worst_client_fpr"
    ALERT_BURDEN = "alert_burden"
    FPR_TARGET_ATTAINMENT = "fpr_target_attainment"


class DetectionQualityMetric(StrEnum):
    AUROC = "auroc"
    MACRO_F1 = "macro_f1"
    P10_MACRO_F1 = "p10_macro_f1"
    BALANCED_ACCURACY = "balanced_accuracy"
    WORST_CLIENT_BA = "worst_client_ba"


class EquityMetric(StrEnum):
    JAIN_INDEX = "jain_index"
    GINI_COEFFICIENT = "gini_coefficient"
    WITHIN_CLUSTER_DISPERSION = "within_cluster_dispersion"
    ACROSS_CLUSTER_DISPERSION = "across_cluster_dispersion"


class EstimationMetric(StrEnum):
    QUANTILE_ESTIMATION_ERROR = "quantile_estimation_error"
    THRESHOLD_VARIANCE = "threshold_variance"
    CALIBRATION_SAMPLE_EFFICIENCY = "calibration_sample_efficiency"
    ELIGIBILITY_COVERAGE = "eligibility_coverage"
    CONFORMAL_COVERAGE = "conformal_coverage"


class ClusterMetric(StrEnum):
    ADJUSTED_RAND_INDEX = "adjusted_rand_index"
    SILHOUETTE = "silhouette"


class DistributionMetric(StrEnum):
    PAIRWISE_JS_DIVERGENCE = "pairwise_js_divergence"


class DiagnosticRatio(StrEnum):
    ABSORPTION_RATIO = "absorption_ratio"
    BETWEEN_RATIO = "between_ratio"
    RECOVERY_RATIO = "recovery_ratio"


class ResourceMetric(StrEnum):
    COMMUNICATION_BYTES_PER_ROUND = "communication_bytes_per_round"
    TOTAL_COMMUNICATION_BYTES = "total_communication_bytes"
    CLIENT_TO_SERVER_BYTES = "client_to_server_bytes"
    SERVER_TO_CLIENT_BYTES = "server_to_client_bytes"
    THRESHOLD_MESSAGE_BYTES = "threshold_message_bytes"
    CHECKPOINT_STORAGE_BYTES = "checkpoint_storage_bytes"
    SCORE_ARTIFACT_STORAGE_BYTES = "score_artifact_storage_bytes"
    RESULT_STORAGE_BYTES = "result_storage_bytes"


type MetricId = (
    OperatingPointMetric
    | DetectionQualityMetric
    | EquityMetric
    | EstimationMetric
    | ClusterMetric
    | DistributionMetric
    | DiagnosticRatio
    | ResourceMetric
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricMapEntry[MetricValue]:
    metric: MetricId
    value: MetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricMap[MetricValue]:
    entries: tuple[MetricMapEntry[MetricValue], ...]

    def __post_init__(self) -> None:
        metrics = tuple(entry.metric for entry in self.entries)
        if len(set(metrics)) != len(metrics):
            raise DomainValidationError(
                detail="metric map must not contain duplicate metric identifiers",
                value=repr(metrics),
                constraint="unique MetricId keys",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricSpec:
    metric: MetricId
    family: MetricFamily
    is_control: bool
    needs_eligible_only: bool
    higher_is_better: bool


METRIC_SPECS: tuple[MetricSpec, ...] = (
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.OPERATING_POINT,
            is_control=False,
            needs_eligible_only=True,
            higher_is_better=False,
        )
        for metric in (
            OperatingPointMetric.FPR,
            OperatingPointMetric.CV_FPR,
            OperatingPointMetric.CV_TPR,
            OperatingPointMetric.IQR_FPR,
            OperatingPointMetric.FPR_RANGE,
            OperatingPointMetric.WORST_CLIENT_FPR,
            OperatingPointMetric.ALERT_BURDEN,
        )
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.OPERATING_POINT,
            is_control=False,
            needs_eligible_only=True,
            higher_is_better=True,
        )
        for metric in (OperatingPointMetric.TPR, OperatingPointMetric.FPR_TARGET_ATTAINMENT)
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.DETECTION_QUALITY,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (
            DetectionQualityMetric.MACRO_F1,
            DetectionQualityMetric.P10_MACRO_F1,
            DetectionQualityMetric.BALANCED_ACCURACY,
            DetectionQualityMetric.WORST_CLIENT_BA,
        )
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.DETECTION_QUALITY,
            is_control=True,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (DetectionQualityMetric.AUROC,)
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.EQUITY,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (EquityMetric.JAIN_INDEX,)
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.EQUITY,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=False,
        )
        for metric in (
            EquityMetric.GINI_COEFFICIENT,
            EquityMetric.WITHIN_CLUSTER_DISPERSION,
            EquityMetric.ACROSS_CLUSTER_DISPERSION,
        )
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.ESTIMATION,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=False,
        )
        for metric in (
            EstimationMetric.QUANTILE_ESTIMATION_ERROR,
            EstimationMetric.THRESHOLD_VARIANCE,
        )
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.ESTIMATION,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (
            EstimationMetric.CALIBRATION_SAMPLE_EFFICIENCY,
            EstimationMetric.ELIGIBILITY_COVERAGE,
            EstimationMetric.CONFORMAL_COVERAGE,
        )
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.CLUSTER,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (ClusterMetric.ADJUSTED_RAND_INDEX, ClusterMetric.SILHOUETTE)
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.DISTRIBUTION,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (DistributionMetric.PAIRWISE_JS_DIVERGENCE,)
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.DIAGNOSTIC,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=True,
        )
        for metric in (
            DiagnosticRatio.ABSORPTION_RATIO,
            DiagnosticRatio.BETWEEN_RATIO,
            DiagnosticRatio.RECOVERY_RATIO,
        )
    ),
    *(
        MetricSpec(
            metric=metric,
            family=MetricFamily.RESOURCE,
            is_control=False,
            needs_eligible_only=False,
            higher_is_better=False,
        )
        for metric in ResourceMetric
    ),
)
