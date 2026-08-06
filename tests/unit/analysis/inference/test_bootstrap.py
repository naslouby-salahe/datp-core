from datp_core.analysis.contrasts import FixedScorePairProvenance, PairedContrast, SupplementaryPairedAnalysisPlan
from datp_core.analysis.inference.bootstrap.contracts import (
    BcaAdjustment,
    BcaOutcome,
    BootstrapInterval,
)
from datp_core.analysis.inference.bootstrap.estimation import (
    paired_bca_interval,
    supplementary_paired_bca_interval,
)
from datp_core.analysis.scientific_decision import ScientificDecision, decide_confirmatory
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.seeds import SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL, PairedInferenceProtocol


def test_paired_bca_is_deterministic_and_uses_protocol_metadata() -> None:
    values = contrasts()
    first = paired_bca_interval(
        values,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(73),
    )
    second = paired_bca_interval(
        values,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(73),
    )
    assert first.outcome is BcaOutcome.AVAILABLE
    assert first == second
    assert first.method is CONFIRMATORY_INFERENCE_PROTOCOL.interval_method
    assert first.replicate_count == CONFIRMATORY_INFERENCE_PROTOCOL.bootstrap_replicates


def test_empty_pairs_are_blocked_without_a_fabricated_point_estimate() -> None:
    result = paired_bca_interval(
        (),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(73),
    )
    assert result.outcome is BcaOutcome.BLOCKED
    assert result.point_estimate is None


def test_supplementary_interval_cannot_be_promoted_to_confirmatory() -> None:
    seed_cohort = SeedCohort(values=tuple(Seed(seed) for seed in range(1, 5)))
    protocol = PairedInferenceProtocol(
        **{
            **CONFIRMATORY_INFERENCE_PROTOCOL.model_dump(),
            "seed_cohort": seed_cohort,
        }
    )
    plan = SupplementaryPairedAnalysisPlan(
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        seed_cohort=seed_cohort,
        inference_protocol=protocol,
    )
    result = supplementary_paired_bca_interval(
        tuple(
            _contrast(
                seed,
                PopulationId.EDGE_SENSOR_GROUPS,
                EvidenceRole.EXTERNAL_VALIDATION,
            )
            for seed in range(1, 5)
        ),
        plan=plan,
        analysis_seed=Seed(73),
    )
    assert result.outcome is BcaOutcome.AVAILABLE


def test_confirmatory_decision_uses_the_interval_only() -> None:
    interval = BootstrapInterval.available(
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(3),
        point_estimate=MetricValue(0.2),
        lower_bound=MetricValue(0.01),
        upper_bound=MetricValue(0.4),
        adjustment=BcaAdjustment(
            bias_correction=MetricValue(0.0),
            acceleration=MetricValue(0.0),
        ),
    )
    result = decide_confirmatory(interval)
    assert result.decision is ScientificDecision.SUPPORTED
    assert result.availability is AvailabilityStatus.AVAILABLE


def test_bca_handles_ties_with_identical_deltas_as_degenerate() -> None:
    values = tuple(
        _contrast(
            seed,
            PopulationId.NBAIOT_NATURAL_DEVICES,
            EvidenceRole.CONFIRMATORY,
            shared=MetricValue(0.05),
            local=MetricValue(0.02),
        )
        for seed in range(10)
    )
    result = paired_bca_interval(
        values,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(11),
    )
    assert result.outcome is BcaOutcome.DEGENERATE


def contrasts() -> tuple[PairedContrast, ...]:
    return tuple(
        _contrast(
            seed,
            PopulationId.NBAIOT_NATURAL_DEVICES,
            EvidenceRole.CONFIRMATORY,
        )
        for seed in range(10)
    )


def _fixed_score() -> FixedScorePairProvenance:
    checksum = Checksum("a" * 64)
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


def _contrast(
    seed: int,
    population: PopulationId,
    role: EvidenceRole,
    *,
    shared: MetricValue | None = None,
    local: MetricValue | None = None,
) -> PairedContrast:
    local_value = local if local is not None else MetricValue(0.02 + seed / 10_000)
    shared_value = shared if shared is not None else MetricValue(local_value.value + 0.01 + seed / 100_000)
    return PairedContrast(
        coordinate=FederatedTrainingCoordinate(
            population=population,
            training_seed=Seed(seed),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=None,
        ),
        evidence_role=role,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=shared_value,
        right_value=local_value,
        fixed_score=_fixed_score(),
    )
