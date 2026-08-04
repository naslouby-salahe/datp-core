"""Analysis-stage persistence, typed protocol, and mechanism serialization contracts."""

from json import loads
from pathlib import Path

from datp_core.analysis.mechanisms import GroupDispersionObservation, grouped_dispersion
from datp_core.analysis.models import MultiplicityPlan, PairedContrast, PValue
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
from datp_core.domain.values import ClusterIndex, MetricValue, Ratio, Seed, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.orchestration.stages.analyze import AnalyzeRequest, analyze_stage
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL


def test_analyze_stage_persists_protocol_mechanisms_and_reuses_document(tmp_path: Path) -> None:
    mechanism = grouped_dispersion(
        (
            GroupDispersionObservation(
                group_index=ClusterIndex(0),
                thresholds=(ThresholdValue(0.2), ThresholdValue(0.4)),
                false_positive_rates=(Ratio(0.1), Ratio(0.2)),
            ),
        )
    )
    request = AnalyzeRequest(
        contrasts=tuple(_contrast(seed) for seed in range(10)),
        inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(31),
        output_directory=tmp_path / "analysis",
        overwrite=False,
        multiplicity_plan=MultiplicityPlan(
            family_name="predeclared_supportive_family",
            raw_p_values=(PValue(0.01), PValue(0.04)),
            alpha=Ratio(0.05),
        ),
        mechanisms=(mechanism,),
    )
    first = analyze_stage(request)
    second = analyze_stage(request)
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert second.wilcoxon.availability is AvailabilityStatus.AVAILABLE
    assert second.multiplicity is not None
    assert second.mechanisms == (mechanism,)

    document = loads((request.output_directory / "analysis.json").read_text())
    protocol = document["inference_protocol"]
    assert protocol["interval_method"] == "bca_paired_arithmetic_mean"
    assert protocol["wilcoxon_alternative"] == "two-sided"
    assert protocol["wilcoxon_zero_method"] == "pratt"
    assert protocol["wilcoxon_computation_method"] == "asymptotic"
    assert document["mechanisms"][0]["group_sizes"] == [2]


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
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=shared,
        right_value=local,
    )
