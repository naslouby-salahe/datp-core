from datp_core.analysis.contrasts import PairedContrast, SupplementaryPairedAnalysisPlan
from datp_core.analysis.inference.bootstrap.contracts import (
    BcaAdjustment,
    BcaOutcome,
    BootstrapInterval,
)
from datp_core.analysis.inference.bootstrap.estimation import (
    paired_bca_interval,
    supplementary_paired_bca_interval,
)
from datp_core.analysis.scientific_decision import decide_confirmatory
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    ScientificDecision,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import MetricValue, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.models import SeedCohort
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


def contrasts() -> tuple[PairedContrast, ...]:
    return tuple(
        _contrast(
            seed,
            PopulationId.NBAIOT_NATURAL_DEVICES,
            EvidenceRole.CONFIRMATORY,
        )
        for seed in range(10)
    )


def _contrast(
    seed: int,
    population: PopulationId,
    role: EvidenceRole,
) -> PairedContrast:
    local = MetricValue(0.02 + seed / 10_000)
    shared = MetricValue(local.value + 0.01 + seed / 100_000)
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
        left_value=shared,
        right_value=local,
    )
