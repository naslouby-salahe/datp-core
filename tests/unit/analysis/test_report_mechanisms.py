from pathlib import Path

from datp_core.analysis.contrasts import FixedScorePairProvenance, PairedContrast
from datp_core.analysis.mechanisms.divergence import ClientScoreVector, jensen_shannon_divergence
from datp_core.analysis.preparation import ConfirmatoryAnalysisRequest, prepare_confirmatory_analysis
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.reporting.export import export_analysis_report


def test_analysis_report_contains_actual_mechanism_values(tmp_path: Path) -> None:
    clients = (
        ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, "a", PopulationIdentityKind.PHYSICAL_DEVICES),
        ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, "b", PopulationIdentityKind.PHYSICAL_DEVICES),
    )
    divergence = jensen_shannon_divergence(
        (
            ClientScoreVector(client=clients[0], scores=(MetricValue(0.1), MetricValue(0.2))),
            ClientScoreVector(client=clients[1], scores=(MetricValue(0.8), MetricValue(0.9))),
        ),
        source_score_checksum=Checksum("e" * 64),
    )
    document = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=tuple(_contrast(seed) for seed in range(10)),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=Seed(31),
            mechanisms=(divergence,),
        )
    )
    path = export_analysis_report(document, tmp_path / "report.md")
    text = path.read_text(encoding="utf-8")
    assert "jensen_shannon_score_divergence" in text
    assert "Aggregate JS distance" in text
    assert "Paired Seed Values" in text
    assert str(document.interval.point_estimate.value if document.interval.point_estimate else "")[:4] in text


def _fixed_score() -> FixedScorePairProvenance:
    checksum = Checksum("f" * 64)
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
        left_value=MetricValue(0.05 + seed / 10_000),
        right_value=MetricValue(0.02),
        fixed_score=_fixed_score(),
    )
