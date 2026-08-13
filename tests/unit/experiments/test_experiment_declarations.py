from datp_core.core.identifiers import EvidenceRole, ExperimentId
from datp_core.experiments.registry import EXPERIMENTS


def test_exactly_one_confirmatory_experiment_exists() -> None:
    assert tuple(item.role for item in EXPERIMENTS).count(EvidenceRole.CONFIRMATORY) == 1
    assert tuple(item.id for item in EXPERIMENTS) == tuple(ExperimentId)


def test_supporting_evidence_families_have_locked_nonconfirmatory_roles() -> None:
    roles = {item.id: item.role for item in EXPERIMENTS}

    assert {
        experiment: roles[experiment]
        for experiment in (
            ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
            ExperimentId.QUANTILE_SENSITIVITY,
            ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY,
            ExperimentId.CALIBRATION_SIZE_ABLATION,
            ExperimentId.CALIBRATION_COLD_START_ONBOARDING,
            ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY,
        )
    } == {
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY: EvidenceRole.SUPPORTIVE,
        ExperimentId.QUANTILE_SENSITIVITY: EvidenceRole.SUPPORTIVE,
        ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY: EvidenceRole.SUPPORTIVE,
        ExperimentId.CALIBRATION_SIZE_ABLATION: EvidenceRole.SUPPORTIVE,
        ExperimentId.CALIBRATION_COLD_START_ONBOARDING: EvidenceRole.SUPPORTIVE,
        ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY: EvidenceRole.SUPPORTIVE,
    }
    assert {
        experiment: roles[experiment]
        for experiment in (
            ExperimentId.FIXED_SHRINKAGE_CURVE,
            ExperimentId.SIZE_AWARE_SHRINKAGE,
            ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        )
    } == {
        ExperimentId.FIXED_SHRINKAGE_CURVE: EvidenceRole.THRESHOLD_VARIANT,
        ExperimentId.SIZE_AWARE_SHRINKAGE: EvidenceRole.THRESHOLD_VARIANT,
        ExperimentId.LOCAL_CONFORMAL_COVERAGE: EvidenceRole.THRESHOLD_VARIANT,
    }
    assert {
        experiment: roles[experiment]
        for experiment in (
            ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
            ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        )
    } == {
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON: EvidenceRole.COMPARATOR,
        ExperimentId.FEDERATED_QUANTILE_ESTIMATION: EvidenceRole.COMPARATOR,
    }
    assert {
        experiment: roles[experiment]
        for experiment in (
            ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION,
            ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
            ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
            ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        )
    } == {
        ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION: EvidenceRole.MECHANISM,
        ExperimentId.FAMILY_AND_GROUPED_GRANULARITY: EvidenceRole.MECHANISM,
        ExperimentId.PER_CLIENT_SCORE_GEOMETRY: EvidenceRole.MECHANISM,
        ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION: EvidenceRole.MECHANISM,
        ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF: EvidenceRole.MECHANISM,
    }
    assert {
        experiment: roles[experiment] for experiment in (ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,)
    } == {
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY: EvidenceRole.EXPLORATORY,
    }
    assert {
        experiment: roles[experiment]
        for experiment in (
            ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
            ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
            ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
        )
    } == {
        ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION: EvidenceRole.EXTERNAL_VALIDATION,
        ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY: EvidenceRole.APPLICABILITY_BOUNDARY,
        ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST: EvidenceRole.TRAINING_STRESS_TEST,
        ExperimentId.FEDAVG_LOCAL_FINE_TUNING: EvidenceRole.TRAINING_STRESS_TEST,
        ExperimentId.DITTO_ABSORPTION_STRESS_TEST: EvidenceRole.TRAINING_STRESS_TEST,
        ExperimentId.EDGE_ONE_SHOT_RECALIBRATION: EvidenceRole.TEMPORAL_BOUNDARY,
        ExperimentId.GROUP_MEDIAN_SUPPLEMENT: EvidenceRole.EXPLORATORY,
    }
