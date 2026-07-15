from datp_core.domain.evaluation.metrics import (
    METRIC_SPECS,
    ClusterMetric,
    DetectionQualityMetric,
    DiagnosticRatio,
    DistributionMetric,
    EquityMetric,
    EstimationMetric,
    MetricFamily,
    MetricSpec,
    OperatingPointMetric,
    ResourceMetric,
)


def test_metric_families_have_disjoint_serialized_identifiers() -> None:
    metric_enums = (
        OperatingPointMetric,
        DetectionQualityMetric,
        EquityMetric,
        EstimationMetric,
        ClusterMetric,
        DistributionMetric,
        DiagnosticRatio,
        ResourceMetric,
    )
    values = tuple(member.value for enum_type in metric_enums for member in enum_type)
    assert len(values) == len(set(values))
    assert tuple(MetricFamily) == (
        MetricFamily.OPERATING_POINT,
        MetricFamily.DETECTION_QUALITY,
        MetricFamily.EQUITY,
        MetricFamily.ESTIMATION,
        MetricFamily.CLUSTER,
        MetricFamily.DISTRIBUTION,
        MetricFamily.DIAGNOSTIC,
        MetricFamily.RESOURCE,
    )


def test_cv_fpr_is_primary_and_eligible_only() -> None:
    spec = MetricSpec(
        metric=OperatingPointMetric.CV_FPR,
        family=MetricFamily.OPERATING_POINT,
        is_control=False,
        needs_eligible_only=True,
        higher_is_better=False,
    )
    assert not spec.is_control
    assert spec.needs_eligible_only


def test_auroc_is_explicitly_a_control_metric() -> None:
    spec = MetricSpec(
        metric=DetectionQualityMetric.AUROC,
        family=MetricFamily.DETECTION_QUALITY,
        is_control=True,
        needs_eligible_only=False,
        higher_is_better=True,
    )
    assert spec.is_control


def test_metric_specifications_cover_each_metric_exactly_once() -> None:
    all_metrics = {
        metric
        for enum_type in (
            OperatingPointMetric,
            DetectionQualityMetric,
            EquityMetric,
            EstimationMetric,
            ClusterMetric,
            DistributionMetric,
            DiagnosticRatio,
            ResourceMetric,
        )
        for metric in enum_type
    }
    assert {spec.metric for spec in METRIC_SPECS} == all_metrics
    assert len(METRIC_SPECS) == len(all_metrics)
    cv_fpr_spec = next(spec for spec in METRIC_SPECS if spec.metric is OperatingPointMetric.CV_FPR)
    auroc_spec = next(spec for spec in METRIC_SPECS if spec.metric is DetectionQualityMetric.AUROC)
    assert not cv_fpr_spec.is_control and cv_fpr_spec.needs_eligible_only
    assert auroc_spec.is_control
