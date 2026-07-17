import pytest
from pydantic import BaseModel, ValidationError

from datp_core.config.schemas.artifacts import ArtifactConfig, ArtifactSerializationConfig
from datp_core.config.schemas.execution import (
    ExecutionConfig,
    ParallelismConfig,
    RecoveryConfig,
    ResourceBudgetConfig,
    ResourcePressureConfig,
    StageExecutionConfig,
    StreamingChunkConfig,
)
from datp_core.config.schemas.reporting import ReportingConfig, ReportingFormatConfig
from datp_core.config.schemas.scientific import (
    AbsorptionGateConfig,
    BcaBootstrapStatisticalConfig,
    CalibrationSizeFallbackThresholdConfig,
    CanonicalTemporalConfig,
    CentralizedComparatorConfig,
    CliffsDeltaStatisticalConfig,
    ClusterThresholdConfig,
    ConformalThresholdConfig,
    DeviceClientPartitionConfig,
    DirichletPartitionConfig,
    EvaluationConfig,
    FamilyThresholdConfig,
    FedAvgFederationConfig,
    FedProxFederationConfig,
    FedStatsBenignThresholdConfig,
    FedStatsSupplementaryKConfig,
    FilePseudoClientPartitionConfig,
    GroupClientPartitionConfig,
    LinearRegressionStatisticalConfig,
    LocalThresholdConfig,
    NaturalDevicePartitionConfig,
    PercentileBootstrapStatisticalConfig,
    RegimeAPreprocessingConfig,
    RegimeAStaticSplitConfig,
    RobustClusterMedianThresholdConfig,
    ScientificConfig,
    SharedThresholdConfig,
    ShrinkageThresholdConfig,
    SpearmanStatisticalConfig,
    TemporalRecoveryGateConfig,
    WilcoxonStatisticalConfig,
)


def _scientific_payload_json() -> str:
    return """
    {
      "protocol_track": "complete",
      "partitioning": {"strategy": "natural_device", "regime": "a"},
      "threshold_constructions": [{
        "kind": "shared",
        "percentile": "0.95",
        "construction": "mean",
        "estimator": "higher"
      }],
      "evaluation": {"primary": "cv_fpr", "controls": ["fpr"]},
      "statistics": {
        "method": "bca_bootstrap",
        "confidence": "0.95",
        "paired_seed_count": 10,
        "resamples": 1000
      },
      "federation": {
        "aggregation": "fedavg",
        "local_epochs": 1,
        "participation": "full",
        "rounds_max": 200,
        "fedprox_mu": null,
        "selection_source": "not_applicable"
      },
      "canonical_temporal": null
    }
    """


def test_discriminated_threshold_union_requires_an_explicit_tag() -> None:
    missing_tag_payload = _scientific_payload_json().replace('"kind": "shared",', "")

    with pytest.raises(ValidationError):
        ScientificConfig.model_validate_json(missing_tag_payload)


def test_evaluation_primary_is_locked_to_cv_fpr() -> None:
    with pytest.raises(ValidationError):
        EvaluationConfig.model_validate_json('{"primary": "cv_tpr", "controls": ["fpr"]}')


@pytest.mark.parametrize(
    ("field", "value"),
    (("method", "percentile_bootstrap"), ("confidence", "0.90"), ("paired_seed_count", 5)),
)
def test_confirmatory_statistics_shape_is_locked(field: str, value: str | int) -> None:
    match field:
        case "method":
            old, new = '"method": "bca_bootstrap"', f'"method": "{value}"'
        case "confidence":
            old, new = '"confidence": "0.95"', f'"confidence": "{value}"'
        case "paired_seed_count":
            old, new = '"paired_seed_count": 10', f'"paired_seed_count": {value}'
        case _:
            pytest.fail(f"unexpected confirmatory field: {field}")

    payload = _scientific_payload_json().replace(old, new)

    with pytest.raises(ValidationError):
        ScientificConfig.model_validate_json(payload)


def test_boundary_schema_fields_have_no_defaults() -> None:
    schemas: tuple[type[BaseModel], ...] = (
        SharedThresholdConfig,
        LocalThresholdConfig,
        FamilyThresholdConfig,
        ClusterThresholdConfig,
        RobustClusterMedianThresholdConfig,
        ShrinkageThresholdConfig,
        CalibrationSizeFallbackThresholdConfig,
        ConformalThresholdConfig,
        FedStatsBenignThresholdConfig,
        BcaBootstrapStatisticalConfig,
        PercentileBootstrapStatisticalConfig,
        WilcoxonStatisticalConfig,
        CliffsDeltaStatisticalConfig,
        SpearmanStatisticalConfig,
        LinearRegressionStatisticalConfig,
        EvaluationConfig,
        ScientificConfig,
        FedAvgFederationConfig,
        FedProxFederationConfig,
        CanonicalTemporalConfig,
        CentralizedComparatorConfig,
        RegimeAStaticSplitConfig,
        RegimeAPreprocessingConfig,
        AbsorptionGateConfig,
        TemporalRecoveryGateConfig,
        FedStatsSupplementaryKConfig,
        NaturalDevicePartitionConfig,
        FilePseudoClientPartitionConfig,
        DeviceClientPartitionConfig,
        GroupClientPartitionConfig,
        DirichletPartitionConfig,
        ExecutionConfig,
        ResourceBudgetConfig,
        StageExecutionConfig,
        ParallelismConfig,
        ResourcePressureConfig,
        RecoveryConfig,
        StreamingChunkConfig,
        ArtifactConfig,
        ArtifactSerializationConfig,
        ReportingConfig,
        ReportingFormatConfig,
    )

    assert all(field.is_required() for schema in schemas for field in schema.model_fields.values())
