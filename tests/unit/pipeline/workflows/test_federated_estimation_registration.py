"""Workflow registration and contract tests for federated threshold estimation experiments."""

from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.pipeline.workflows import require_experiment_declaration
from datp_core.pipeline.workflows.campaign import (
    REGISTERED_WORKFLOW_EXPERIMENTS,
    _CAMPAIGN_ORDER,
)
from datp_core.pipeline.workflows.federated_threshold_estimation import (
    federated_benign_statistics_comparison_analysis_marker_present,
    federated_quantile_estimation_analysis_marker_present,
    fixed_coefficient_statistics_sensitivity_analysis_marker_present,
)

_COMPARISON = ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON
_QUANTILE = ExperimentId.FEDERATED_QUANTILE_ESTIMATION
_FIXED_COEFFICIENT = ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY

_FEDERATED_ESTIMATION_EXPERIMENTS = (_COMPARISON, _QUANTILE, _FIXED_COEFFICIENT)


def test_all_three_experiments_are_registered_in_campaign_order() -> None:
    for experiment_id in _FEDERATED_ESTIMATION_EXPERIMENTS:
        assert experiment_id in REGISTERED_WORKFLOW_EXPERIMENTS
        assert experiment_id in _CAMPAIGN_ORDER


def test_federated_benign_statistics_comparison_declaration_is_locked() -> None:
    declaration = require_experiment_declaration(_COMPARISON)
    assert declaration.role is EvidenceRole.THRESHOLD_VARIANT
    assert declaration.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert declaration.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert declaration.readiness is ExperimentReadiness.DECLARED
    assert FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS in declaration.federated_thresholds
    assert FederatedThresholdMethod.SHARED_THRESHOLD in declaration.federated_thresholds
    assert FederatedThresholdMethod.LOCAL_THRESHOLD in declaration.federated_thresholds
    assert FederatedThresholdMethod.POOLED_SHARED_QUANTILE in declaration.federated_thresholds
    assert FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD in declaration.federated_thresholds


def test_federated_quantile_estimation_declaration_is_locked() -> None:
    declaration = require_experiment_declaration(_QUANTILE)
    assert declaration.role is EvidenceRole.THRESHOLD_VARIANT
    assert declaration.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert declaration.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS in declaration.federated_thresholds


def test_fixed_coefficient_statistics_sensitivity_declaration_is_locked() -> None:
    declaration = require_experiment_declaration(_FIXED_COEFFICIENT)
    assert declaration.role is EvidenceRole.THRESHOLD_VARIANT
    assert declaration.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert declaration.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS in declaration.federated_thresholds
    assert FederatedThresholdMethod.SHARED_THRESHOLD in declaration.federated_thresholds
    assert FederatedThresholdMethod.LOCAL_THRESHOLD in declaration.federated_thresholds


def test_fixed_coefficient_declaration_excludes_family_and_cluster_thresholds() -> None:
    declaration = require_experiment_declaration(_FIXED_COEFFICIENT)
    assert FederatedThresholdMethod.FAMILY_THRESHOLD not in declaration.federated_thresholds
    assert FederatedThresholdMethod.CLUSTER_THRESHOLD not in declaration.federated_thresholds


def test_comparison_experiment_includes_five_threshold_methods() -> None:
    declaration = require_experiment_declaration(_COMPARISON)
    assert len(declaration.federated_thresholds) == 5


def test_fixed_coefficient_experiment_includes_three_threshold_methods() -> None:
    declaration = require_experiment_declaration(_FIXED_COEFFICIENT)
    assert len(declaration.federated_thresholds) == 3


def test_analysis_markers_are_callable_and_return_bool() -> None:
    assert isinstance(federated_benign_statistics_comparison_analysis_marker_present(_COMPARISON), bool)
    assert isinstance(federated_quantile_estimation_analysis_marker_present(_QUANTILE), bool)
    assert isinstance(
        fixed_coefficient_statistics_sensitivity_analysis_marker_present(_FIXED_COEFFICIENT), bool
    )


def test_threshold_variant_experiments_are_not_confirmatory() -> None:
    for experiment_id in _FEDERATED_ESTIMATION_EXPERIMENTS:
        declaration = require_experiment_declaration(experiment_id)
        assert declaration.role is not EvidenceRole.CONFIRMATORY
