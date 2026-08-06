from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.analysis.temporal import (
    TemporalInterpretation,
    decide_temporal_campaign,
    temporal_recovery,
)
from datp_core.domain.enums import AvailabilityStatus, ExperimentId, FederatedThresholdMethod
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT


def test_scientific_decision_member_set_is_exact_and_unique() -> None:
    assert set(ScientificDecision.__members__) == {
        "SUPPORTED",
        "DIRECTIONAL_INCONCLUSIVE",
        "NO_OBSERVED_ADVANTAGE",
        "OPPOSITE_DIRECTION",
        "PARTIAL_ABSORPTION",
        "FULL_ABSORPTION",
        "BOUNDARY_RESULT",
        "INFEASIBLE",
        "BLOCKED",
    }
    values = tuple(member.value for member in ScientificDecision)
    assert len(values) == len(set(values))
    assert all(value.islower() for value in values)


def test_material_drift_with_recovery_is_supported_only_at_campaign_level() -> None:
    # drift=0.20, recovered=0.18, ratio=0.9 >= 0.25 material recovery floor
    records = tuple(_recovery(seed.value, 0.10, 0.30, 0.12) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert all(
        record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
        for record in records
    )
    campaign = decide_temporal_campaign(records)
    assert campaign.decision is ScientificDecision.SUPPORTED


def test_tiny_positive_recovery_is_not_material_support() -> None:
    # drift=0.20, recovered=0.001, ratio=0.005 < 0.25 material recovery floor
    records = tuple(_recovery(seed.value, 0.10, 0.30, 0.299) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert all(
        record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY
        for record in records
    )
    assert decide_temporal_campaign(records).decision is ScientificDecision.BOUNDARY_RESULT


def test_single_seed_never_yields_publication_supported() -> None:
    result = temporal_recovery(
        seed=Seed(0),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.30),
        recalibrated_future_cv=MetricValue(0.12),
    )
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
    assert decide_temporal_campaign((result,)).decision is ScientificDecision.BLOCKED


def test_incomplete_seed_cohort_is_blocked() -> None:
    records = tuple(_recovery(seed, 0.10, 0.30, 0.12) for seed in range(5))
    assert decide_temporal_campaign(records).decision is ScientificDecision.BLOCKED


def test_duplicate_seed_campaign_is_blocked() -> None:
    left = _recovery(0, 0.1, 0.3, 0.15)
    right = _recovery(0, 0.1, 0.3, 0.15)
    assert decide_temporal_campaign((left, right)).decision is ScientificDecision.BLOCKED


def test_material_drift_without_recovery_is_a_boundary_result() -> None:
    records = tuple(_recovery(seed.value, 0.10, 0.30, 0.35) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert all(
        record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY for record in records
    )
    assert records[0].availability is AvailabilityStatus.AVAILABLE
    assert decide_temporal_campaign(records).decision is ScientificDecision.BOUNDARY_RESULT


def test_no_material_degradation_keeps_recovery_ratio_undefined() -> None:
    result = temporal_recovery(
        seed=Seed(3),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        static_reference_cv=MetricValue(0.20),
        frozen_future_cv=MetricValue(0.25),
        recalibrated_future_cv=MetricValue(0.10),
    )
    assert result.recovery_ratio is None
    assert result.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
    records = tuple(_recovery(seed.value, 0.20, 0.25, 0.10) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert decide_temporal_campaign(records).decision is ScientificDecision.BOUNDARY_RESULT


def test_opposite_temporal_movement_is_preserved() -> None:
    records = tuple(_recovery(seed.value, 0.30, 0.10, 0.20) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert records[0].interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
    assert decide_temporal_campaign(records).decision is ScientificDecision.OPPOSITE_DIRECTION


def test_mixed_method_campaign_is_blocked() -> None:
    left = _recovery(1, 0.1, 0.3, 0.15, method=FederatedThresholdMethod.LOCAL_THRESHOLD)
    right = _recovery(1, 0.1, 0.3, 0.15, method=FederatedThresholdMethod.SHARED_THRESHOLD)
    decision = decide_temporal_campaign((left, right))
    assert decision.decision is ScientificDecision.BLOCKED


def _recovery(
    seed: int,
    static_cv: float,
    frozen_cv: float,
    recalibrated_cv: float,
    *,
    method: FederatedThresholdMethod = FederatedThresholdMethod.LOCAL_THRESHOLD,
):
    return temporal_recovery(
        seed=Seed(seed),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        threshold_method=method,
        static_reference_cv=MetricValue(static_cv),
        frozen_future_cv=MetricValue(frozen_cv),
        recalibrated_future_cv=MetricValue(recalibrated_cv),
    )
