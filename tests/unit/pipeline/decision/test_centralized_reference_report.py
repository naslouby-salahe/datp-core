from pathlib import Path

import pytest

from datp_core.analysis.metrics.models import AvailableMetric, ConfusionCounts
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import serialize_json_model
from datp_core.core.errors import ReportEvidenceError
from datp_core.core.identifiers import (
    CentralizedModelId,
    CentralizedThresholdMethod,
    EvidenceRole,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.core.numeric import MetricValue, RowCount, Seed, ThresholdValue
from datp_core.detector.training.centralized import CentralizedTrainingCoordinate
from datp_core.experiments.centralized_reference import (
    CIC_CENTRALIZED_REFERENCE,
    NBAIOT_CENTRALIZED_REFERENCE,
    CentralizedReferenceArtifactDirectory,
    CentralizedReferenceReportAsset,
    CentralizedReferenceReportManifest,
    report_centralized_reference,
)
from datp_core.thresholds.centralized import (
    CENTRALIZED_POOLED_METRICS,
    CentralizedDecisionRule,
    CentralizedEvaluationDocument,
    CentralizedEvaluationPublicationAsset,
)


def _evaluation_document(
    seed_value: int, population: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES
) -> CentralizedEvaluationDocument:
    coordinate = CentralizedTrainingCoordinate(
        population=population,
        training_seed=Seed(seed_value),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )
    confusion = ConfusionCounts(
        true_negative=RowCount(900),
        false_positive=RowCount(10),
        true_positive=RowCount(80),
        false_negative=RowCount(10),
        attack_assignment_valid=True,
    )
    metrics = tuple(
        AvailableMetric(metric=metric, value=MetricValue(float(seed_value + 1)))
        for metric in CENTRALIZED_POOLED_METRICS
    )
    return CentralizedEvaluationDocument(
        coordinate=coordinate,
        threshold_method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
        decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
        threshold=ThresholdValue(0.5),
        confusion=confusion,
        evaluation_row_count=RowCount(1000),
        evidence_role=EvidenceRole.SUPPORTIVE,
        score_artifact_checksum=Checksum("a" * 64),
        threshold_checksum=Checksum("b" * 64),
        metrics=metrics,
    )


def _write_independent_reference(
    output_root: Path, population: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES
) -> None:
    root = output_root / CentralizedReferenceArtifactDirectory.ROOT / population.value
    for seed_value in range(10):
        evaluation_directory = root / str(seed_value) / CentralizedReferenceArtifactDirectory.EVALUATION
        document = _evaluation_document(seed_value, population)
        serialize_json_model(document, evaluation_directory / CentralizedEvaluationPublicationAsset.EVALUATION)
        (evaluation_directory / CentralizedEvaluationPublicationAsset.COMPLETE).write_text(
            "complete", encoding="utf-8"
        )
    (root / CentralizedReferenceReportAsset.COMPLETE).write_text("complete", encoding="utf-8")


def test_report_centralized_reference_publishes_validated_b0_evidence(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    _write_independent_reference(output_root)
    report_directory = report_centralized_reference(
        NBAIOT_CENTRALIZED_REFERENCE, output_root=output_root, overwrite=False
    )

    assert (report_directory / CentralizedReferenceReportAsset.MANIFEST).is_file()
    assert (report_directory / CentralizedReferenceReportAsset.PUBLICATION).is_file()
    assert (report_directory / CentralizedReferenceReportAsset.COMPLETE).is_file()
    manifest = CentralizedReferenceReportManifest.model_validate_json(
        (report_directory / CentralizedReferenceReportAsset.MANIFEST).read_text(encoding="utf-8")
    )
    assert len(manifest.evaluations) == 10
    assert manifest.population is PopulationId.NBAIOT_NATURAL_DEVICES
    publication = (report_directory / CentralizedReferenceReportAsset.PUBLICATION).read_text(encoding="utf-8")
    assert "Centralized reference seed 0" in publication
    assert "Centralized reference seed 9" in publication
    assert "privacy-incompatible centralized reference" in publication


def test_report_centralized_reference_publishes_ciciot_b0_evidence(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    _write_independent_reference(output_root, PopulationId.CICIOT_FILE_CLIENTS)
    report_directory = report_centralized_reference(
        CIC_CENTRALIZED_REFERENCE, output_root=output_root, overwrite=False
    )

    assert (report_directory / CentralizedReferenceReportAsset.MANIFEST).is_file()
    assert (report_directory / CentralizedReferenceReportAsset.PUBLICATION).is_file()
    manifest = CentralizedReferenceReportManifest.model_validate_json(
        (report_directory / CentralizedReferenceReportAsset.MANIFEST).read_text(encoding="utf-8")
    )
    assert manifest.population is PopulationId.CICIOT_FILE_CLIENTS
    publication = (report_directory / CentralizedReferenceReportAsset.PUBLICATION).read_text(encoding="utf-8")
    assert "file-defined applicability" in publication
    assert "CICIoT2023" in publication


def test_report_centralized_reference_fails_closed_without_root_completion(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    root = output_root / CentralizedReferenceArtifactDirectory.ROOT / PopulationId.NBAIOT_NATURAL_DEVICES.value
    for seed_value in range(10):
        evaluation_directory = root / str(seed_value) / CentralizedReferenceArtifactDirectory.EVALUATION
        serialize_json_model(
            _evaluation_document(seed_value),
            evaluation_directory / CentralizedEvaluationPublicationAsset.EVALUATION,
        )
        (evaluation_directory / CentralizedEvaluationPublicationAsset.COMPLETE).write_text(
            "complete", encoding="utf-8"
        )
    with pytest.raises(ReportEvidenceError, match="completion marker is missing"):
        report_centralized_reference(NBAIOT_CENTRALIZED_REFERENCE, output_root=output_root, overwrite=False)


def test_report_centralized_reference_fails_closed_without_per_seed_evaluation(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    root = output_root / CentralizedReferenceArtifactDirectory.ROOT / PopulationId.NBAIOT_NATURAL_DEVICES.value
    root.mkdir(parents=True, exist_ok=True)
    (root / CentralizedReferenceReportAsset.COMPLETE).write_text("complete", encoding="utf-8")
    with pytest.raises(ReportEvidenceError, match="evaluation is incomplete for seed 0"):
        report_centralized_reference(NBAIOT_CENTRALIZED_REFERENCE, output_root=output_root, overwrite=False)
