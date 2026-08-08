from datp_core.core.identifiers import EvidenceRole, ExperimentId
from datp_core.experiments.registry import EXPERIMENTS
from datp_core.thresholds.protocols import (
    CALIBRATION_SIZES,
    SAMPLE_STARVED_CALIBRATION_SIZE,
    CalibrationSizeClassification,
    classify_calibration_size,
)


def test_calibration_size_50_is_sample_starved_diagnostic() -> None:
    assert SAMPLE_STARVED_CALIBRATION_SIZE.value == 50
    classification = classify_calibration_size(SAMPLE_STARVED_CALIBRATION_SIZE)
    assert classification is CalibrationSizeClassification.SAMPLE_STARVED_DIAGNOSTIC


def test_other_calibration_sizes_are_feasible_ablation() -> None:
    for size in CALIBRATION_SIZES:
        if size != SAMPLE_STARVED_CALIBRATION_SIZE:
            assert classify_calibration_size(size) is CalibrationSizeClassification.FEASIBLE_ABLATION_SIZE


def test_confirmatory_experiment_never_uses_calibration_size_ablation() -> None:
    confirmatory_experiments = tuple(item for item in EXPERIMENTS if item.role is EvidenceRole.CONFIRMATORY)
    assert len(confirmatory_experiments) > 0
    for experiment in confirmatory_experiments:
        assert experiment.id is not ExperimentId.CALIBRATION_SIZE_ABLATION


def test_sample_starved_calibration_size_excluded_from_confirmatory() -> None:
    confirmatory = next((item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION), None)
    assert confirmatory is not None
    assert confirmatory.role is EvidenceRole.CONFIRMATORY
    assert confirmatory.id is not ExperimentId.CALIBRATION_SIZE_ABLATION
