from pathlib import Path

from datp_core.analysis.contrasts import FixedScorePairProvenance, PairedContrast
from datp_core.domain.enums import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.pipeline.decision.evidence import (
    AnalyzeConfirmatoryEvidenceRequest,
    analyze_confirmatory_evidence,
)
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL


def test_analysis_reuse_loads_and_validates_persisted_json(tmp_path: Path) -> None:
    request = AnalyzeConfirmatoryEvidenceRequest(
        contrasts=tuple(_contrast(seed) for seed in range(10)),
        inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(31),
        output_directory=tmp_path / "analysis",
        overwrite=False,
    )
    first = analyze_confirmatory_evidence(request)
    second = analyze_confirmatory_evidence(request)
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert first.document == second.document
    assert first.complete_digest == second.complete_digest


def test_corrupted_analysis_json_prevents_reuse(tmp_path: Path) -> None:
    request = AnalyzeConfirmatoryEvidenceRequest(
        contrasts=tuple(_contrast(seed) for seed in range(10)),
        inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(31),
        output_directory=tmp_path / "analysis",
        overwrite=False,
    )
    first = analyze_confirmatory_evidence(request)
    document_path = request.output_directory / "analysis.json"
    document_path.write_text(
        document_path.read_text(encoding="utf-8").replace("supported", "blocked"), encoding="utf-8"
    )
    second = analyze_confirmatory_evidence(request)
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.PUBLISHED
    assert second.document.decision.decision.value == "supported"


def _fixed_score() -> FixedScorePairProvenance:
    checksum = Checksum("d" * 64)
    return FixedScorePairProvenance(
        model_checksum=checksum,
        preprocessing_checksum=checksum,
        selected_checkpoint_checksum=checksum,
        split_manifest_checksum=checksum,
        calibration_score_checksum=checksum,
        evaluation_score_checksum=checksum,
        evaluation_label_checksum=checksum,
        source_row_checksum=checksum,
        score_order_checksum=checksum,
        client_inventory_checksum=checksum,
        eligibility_cohort_checksum=checksum,
    )


def _contrast(seed: int) -> PairedContrast:
    return PairedContrast(
        coordinate=FederatedTrainingCoordinate(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            training_seed=Seed(seed),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=None,
        ),
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=MetricValue(0.04 + seed / 10_000),
        right_value=MetricValue(0.02),
        fixed_score=_fixed_score(),
    )
