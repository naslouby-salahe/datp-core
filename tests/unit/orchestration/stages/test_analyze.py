"""Analysis-stage persistence and reuse contracts."""

from pathlib import Path

from datp_core.analysis.inference import PairedContrast
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import MetricValue, Ratio, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.orchestration.stages.analyze import AnalyzeRequest, analyze_stage
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT, CONFIRMATORY_INFERENCE_PROTOCOL


def test_analyze_stage_persists_secondary_and_descriptive_outputs_and_reuses_them(tmp_path: Path) -> None:
    request = AnalyzeRequest(
        contrasts=tuple(_contrast(seed) for seed in range(10)),
        inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        bootstrap_replicates=BOOTSTRAP_REPLICATE_COUNT,
        analysis_seed=Seed(31),
        output_directory=tmp_path / "analysis",
        overwrite=False,
        secondary_family_name="predeclared_supportive_family",
        secondary_p_values=(0.01, 0.04),
        secondary_alpha=Ratio(0.05),
    )

    first = analyze_stage(request)
    second = analyze_stage(request)

    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert second.descriptive.values == tuple(item.delta.value for item in request.contrasts)
    assert second.sign_consistency.total == 10
    assert second.wilcoxon.availability is AvailabilityStatus.AVAILABLE
    assert second.rank_biserial.availability is AvailabilityStatus.AVAILABLE
    assert second.multiplicity is not None
    assert second.multiplicity.adjusted_p_values[0] <= second.multiplicity.adjusted_p_values[1]
    assert (request.output_directory / "analysis.json").is_file()


def _contrast(seed: int) -> PairedContrast:
    local = MetricValue(0.02 + seed / 10_000)
    shared = MetricValue(local.value + 0.01 + seed / 100_000)
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
        seed=Seed(seed),
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        shared_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        local_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        shared_value=shared,
        local_value=local,
        delta=MetricValue(shared.value - local.value),
    )
