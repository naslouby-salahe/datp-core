import numpy as np
import pytest
from scipy import stats

from datp_core.analysis.contrasts import (
    FixedScorePairProvenance,
    PairedContrast,
    PairedContrasts,
    SupplementaryPairedAnalysisPlan,
)
from datp_core.analysis.inference.bootstrap.contracts import (
    BcaAdjustment,
    BcaOutcome,
    BcaReason,
    BootstrapInterval,
)
from datp_core.analysis.inference.bootstrap.estimation import (
    _bca_interval_from_distribution,
    paired_bca_interval,
    supplementary_paired_bca_interval,
)
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.scientific_decision import ScientificDecision, decide_confirmatory
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import MetricValue, Seed, SeedCount
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


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
        PairedContrasts(values=()),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(73),
    )
    assert result.outcome is BcaOutcome.BLOCKED
    assert result.point_estimate is None


def test_paired_contrasts_reject_duplicate_seed_observations() -> None:
    duplicate = _contrast(0, PopulationId.NBAIOT_NATURAL_DEVICES, EvidenceRole.CONFIRMATORY)
    with pytest.raises(ValueError, match="one observation per seed"):
        PairedContrasts(values=(duplicate, duplicate))


def test_supplementary_interval_cannot_be_promoted_to_confirmatory() -> None:
    seed_cohort = SeedCohort(values=tuple(Seed(seed) for seed in range(1, 5)))
    protocol = PairedInferenceProtocol(
        **{
            **CONFIRMATORY_INFERENCE_PROTOCOL.model_dump(),
            "paired_seed_count": SeedCount(4),
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
        PairedContrasts(
            values=tuple(
                _contrast(
                    seed,
                    PopulationId.EDGE_SENSOR_GROUPS,
                    EvidenceRole.EXTERNAL_VALIDATION,
                )
                for seed in range(1, 5)
            )
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


def test_confirmatory_decision_is_not_established_when_bca_is_unavailable() -> None:
    blocked_interval = BootstrapInterval.blocked(
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(3),
        point_estimate=None,
        reason=BcaReason.SEED_COHORT_MISMATCH,
    )
    result = decide_confirmatory(blocked_interval)
    assert result.decision is ScientificDecision.NOT_ESTABLISHED
    assert result.availability is AvailabilityStatus.UNAVAILABLE
    assert result.decision is not ScientificDecision.BLOCKED


def test_bca_handles_ties_with_identical_deltas_as_degenerate() -> None:
    values = PairedContrasts(
        values=tuple(
            _contrast(
                seed,
                PopulationId.NBAIOT_NATURAL_DEVICES,
                EvidenceRole.CONFIRMATORY,
                shared=MetricValue(0.05),
                local=MetricValue(0.02),
            )
            for seed in range(10)
        )
    )
    result = paired_bca_interval(
        values,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(11),
    )
    assert result.outcome is BcaOutcome.DEGENERATE


def test_distribution_bca_computation_preserves_its_degenerate_reason() -> None:
    computation = _bca_interval_from_distribution(
        estimate=MetricValue(1.0),
        deltas=np.array([0.0, 1.0], dtype=np.float64),
        distribution=np.array([0.0, 0.0], dtype=np.float64),
        confidence_level=CONFIRMATORY_INFERENCE_PROTOCOL.confidence_level,
    )
    result = computation.to_bootstrap_interval(
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(73),
        point_estimate=MetricValue(1.0),
    )
    assert result.outcome is BcaOutcome.DEGENERATE
    assert result.reason is BcaReason.INFINITE_BIAS_CORRECTION


def contrasts() -> PairedContrasts:
    return PairedContrasts(
        values=tuple(
            _contrast(
                seed,
                PopulationId.NBAIOT_NATURAL_DEVICES,
                EvidenceRole.CONFIRMATORY,
            )
            for seed in range(10)
        )
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


_ORACLE_DELTAS = (0.10, 0.12, 0.08, 0.15, 0.05, 0.11, 0.09, 0.13, 0.07, 0.14)


def test_bca_interval_matches_an_independently_computed_efron_bca_oracle() -> None:
    values = PairedContrasts(
        values=tuple(
            _contrast(
                seed,
                PopulationId.NBAIOT_NATURAL_DEVICES,
                EvidenceRole.CONFIRMATORY,
                local=MetricValue(0.0),
                shared=MetricValue(delta),
            )
            for seed, delta in enumerate(_ORACLE_DELTAS)
        )
    )
    analysis_seed = Seed(11)
    result = paired_bca_interval(
        values,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=analysis_seed,
    )
    assert result.outcome is BcaOutcome.AVAILABLE
    assert result.point_estimate is not None
    assert result.lower_bound is not None
    assert result.upper_bound is not None
    assert result.adjustment is not None

    deltas = np.array(_ORACLE_DELTAS, dtype=np.float64)
    estimate = float(np.mean(deltas))
    assert result.point_estimate.value == pytest.approx(estimate, abs=1e-12)

    rng = np.random.default_rng(analysis_seed.value)
    replicate_count = CONFIRMATORY_INFERENCE_PROTOCOL.bootstrap_replicates.value
    indexes = rng.integers(0, deltas.size, size=(replicate_count, deltas.size))
    distribution = np.mean(deltas[indexes], axis=1)

    proportion_less = float(np.mean(distribution < estimate))
    expected_bias_correction = float(stats.norm.ppf(proportion_less))
    assert result.adjustment.bias_correction.value == pytest.approx(expected_bias_correction, abs=1e-9)

    leave_one_out_means = np.array([np.mean(np.delete(deltas, index)) for index in range(deltas.size)])
    centered = np.mean(leave_one_out_means) - leave_one_out_means
    expected_acceleration = float(np.sum(centered**3) / (6.0 * np.sum(centered**2) ** 1.5))
    assert result.adjustment.acceleration.value == pytest.approx(expected_acceleration, abs=1e-9)

    confidence_level = CONFIRMATORY_INFERENCE_PROTOCOL.confidence_level.value
    alpha = (1.0 - confidence_level) / 2.0
    z0 = expected_bias_correction
    acceleration = expected_acceleration
    z_lo = z0 + stats.norm.ppf(alpha)
    z_hi = z0 + stats.norm.ppf(1.0 - alpha)
    q_lo = stats.norm.cdf(z0 + z_lo / (1.0 - acceleration * z_lo))
    q_hi = stats.norm.cdf(z0 + z_hi / (1.0 - acceleration * z_hi))
    expected_lower = float(np.quantile(distribution, q_lo, method="linear"))
    expected_upper = float(np.quantile(distribution, q_hi, method="linear"))
    assert result.lower_bound.value == pytest.approx(expected_lower, abs=1e-9)
    assert result.upper_bound.value == pytest.approx(expected_upper, abs=1e-9)


def test_bca_interval_agrees_with_an_independent_scipy_bca_implementation() -> None:
    values = PairedContrasts(
        values=tuple(
            _contrast(
                seed,
                PopulationId.NBAIOT_NATURAL_DEVICES,
                EvidenceRole.CONFIRMATORY,
                local=MetricValue(0.0),
                shared=MetricValue(delta),
            )
            for seed, delta in enumerate(_ORACLE_DELTAS)
        )
    )
    result = paired_bca_interval(
        values,
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(11),
    )
    assert result.outcome is BcaOutcome.AVAILABLE
    assert result.lower_bound is not None
    assert result.upper_bound is not None

    deltas = np.array(_ORACLE_DELTAS, dtype=np.float64)
    reference = stats.bootstrap(
        (deltas,),
        np.mean,
        method="BCa",
        confidence_level=CONFIRMATORY_INFERENCE_PROTOCOL.confidence_level.value,
        n_resamples=CONFIRMATORY_INFERENCE_PROTOCOL.bootstrap_replicates.value,
        rng=np.random.default_rng(0),
    )

    assert result.lower_bound.value == pytest.approx(reference.confidence_interval.low, abs=1e-2)
    assert result.upper_bound.value == pytest.approx(reference.confidence_interval.high, abs=1e-2)
