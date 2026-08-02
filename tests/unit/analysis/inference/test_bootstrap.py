from datp_core.analysis.inference.bootstrap import (
    decide_confirmatory,
    external_paired_bca_interval,
    paired_bca_interval,
)
from datp_core.analysis.models import (
    BcaAdjustment,
    BcaOutcome,
    BcaReason,
    BootstrapInterval,
    ExternalPairedAnalysisPlan,
    PairedContrast,
)
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    ScientificDecision,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import BootstrapReplicateCount, ConfidenceLevel, MetricValue, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT, CONFIRMATORY_INFERENCE_PROTOCOL


def test_paired_bca_requires_exact_canonical_pairs_and_is_deterministic() -> None:
    contrasts = tuple(_contrast(seed) for seed in range(10))

    first = paired_bca_interval(
        contrasts,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        replicate_count=BOOTSTRAP_REPLICATE_COUNT,
        analysis_seed=Seed(73),
    )
    second = paired_bca_interval(
        contrasts,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        replicate_count=BOOTSTRAP_REPLICATE_COUNT,
        analysis_seed=Seed(73),
    )

    assert first.outcome is BcaOutcome.AVAILABLE
    assert first == second


def test_empty_pairs_are_blocked_without_a_fabricated_point_estimate() -> None:
    result = paired_bca_interval(
        (),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        replicate_count=BOOTSTRAP_REPLICATE_COUNT,
        analysis_seed=Seed(73),
    )

    assert result.outcome is BcaOutcome.BLOCKED
    assert result.point_estimate is None


def test_external_interval_is_explicitly_supplementary_and_not_confirmatory() -> None:
    plan = ExternalPairedAnalysisPlan(
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        seed_cohort=(Seed(1), Seed(2), Seed(3), Seed(4)),
        confidence_level=ConfidenceLevel(0.95),
    )
    result = external_paired_bca_interval(
        tuple(_external_contrast(seed) for seed in range(1, 5)),
        plan=plan,
        replicate_count=BOOTSTRAP_REPLICATE_COUNT,
        analysis_seed=Seed(73),
    )

    assert result.outcome is BcaOutcome.AVAILABLE


def test_confirmatory_decision_uses_positive_bca_interval_not_secondary_evidence() -> None:
    interval = BootstrapInterval(
        method=IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
        confidence_level=ConfidenceLevel(0.95),
        replicate_count=BootstrapReplicateCount(10_000),
        analysis_seed=Seed(3),
        point_estimate=MetricValue(0.2),
        lower_bound=MetricValue(0.01),
        upper_bound=MetricValue(0.4),
        adjustment=BcaAdjustment(bias_correction=0.0, acceleration=0.0),
        outcome=BcaOutcome.AVAILABLE,
        reason=BcaReason.NONE,
    )

    result = decide_confirmatory(interval)

    assert result.decision is ScientificDecision.SUPPORTED
    assert result.availability is AvailabilityStatus.AVAILABLE


def _external_contrast(seed: int) -> PairedContrast:
    right = MetricValue(0.02 + seed / 10_000)
    left = MetricValue(right.value + 0.01 + seed / 100_000)
    return PairedContrast(
        coordinate=FederatedTrainingCoordinate(
            population=PopulationId.EDGE_SENSOR_GROUPS,
            training_seed=Seed(seed),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=None,
        ),
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=left,
        right_value=right,
    )


def _contrast(seed: int) -> PairedContrast:
    local = MetricValue(0.02 + seed / 10000)
    shared = MetricValue(local.value + 0.01 + seed / 100000)
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
