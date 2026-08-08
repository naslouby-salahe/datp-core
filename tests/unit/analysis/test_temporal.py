import pytest
from pydantic import ValidationError

from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.analysis.temporal import (
    TemporalClientTrajectory,
    TemporalInterpretation,
    TemporalSeedProvenance,
    decide_temporal_campaign,
    temporal_recovery,
)
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AvailabilityStatus,
    ExperimentId,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
    TemporalState,
)
from datp_core.core.numeric import MetricValue, Ratio, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT
from datp_core.protocols.temporal import TemporalDecisionProtocol, TemporalDeploymentProvenance

_TEST_TEMPORAL_DECISION_PROTOCOL = TemporalDecisionProtocol(
    drift_excess_materiality_threshold=MetricValue(0.1),
    material_recovery_ratio_minimum=Ratio(0.5),
    seed_cohort=BOUNDED_EVIDENCE_SEED_COHORT,
    undefined_recovery_when_drift_not_material=True,
    mixed_seed_publication_support=False,
    require_full_seed_provenance=True,
    require_uncertainty_for_supported=True,
)


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


def test_material_recovery_ratio_minimum_is_half() -> None:
    assert _TEST_TEMPORAL_DECISION_PROTOCOL.material_recovery_ratio_minimum.value == 0.50


def test_material_drift_with_recovery_is_supported_only_at_campaign_level() -> None:
    records = tuple(_recovery(seed.value, 0.10, 0.30, 0.12) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert all(
        record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
        for record in records
    )
    campaign = decide_temporal_campaign(records)
    assert campaign.decision is ScientificDecision.SUPPORTED


def test_tiny_positive_recovery_is_not_material_support() -> None:
    records = tuple(_recovery(seed.value, 0.10, 0.30, 0.299) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert all(
        record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY
        for record in records
    )
    assert decide_temporal_campaign(records).decision is ScientificDecision.BOUNDARY_RESULT


def test_recovery_ratio_just_below_material_floor() -> None:
    result = _recovery(0, 0.10, 0.30, 0.201)
    assert result.recovery_ratio is not None
    assert result.recovery_ratio.value < 0.50
    assert result.recovery_ratio.value > 0.0
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_PARTIAL_OR_WEAK_RECOVERY


def test_recovery_ratio_exactly_at_material_floor() -> None:
    result = _recovery(0, 0.10, 0.50, 0.30)
    assert result.recovery_ratio is not None
    assert result.recovery_ratio.value == pytest.approx(0.50)
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY


def test_recovery_ratio_just_above_material_floor() -> None:
    result = _recovery(0, 0.10, 0.50, 0.298)
    assert result.recovery_ratio is not None
    assert result.recovery_ratio.value > 0.50
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY


def test_zero_recovery_is_without_recovery() -> None:
    result = _recovery(0, 0.10, 0.30, 0.30)
    assert result.recovery_ratio is not None
    assert result.recovery_ratio.value == pytest.approx(0.0)
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY


def test_negative_recovery_is_without_recovery() -> None:
    result = _recovery(0, 0.10, 0.30, 0.40)
    assert result.recovery_ratio is not None
    assert result.recovery_ratio.value < 0.0
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY


def test_single_seed_never_yields_publication_supported() -> None:
    result = _recovery(0, 0.10, 0.30, 0.12)
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
    result = _recovery(3, 0.20, 0.25, 0.10)
    assert result.recovery_ratio is None
    assert result.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
    records = tuple(_recovery(seed.value, 0.20, 0.25, 0.10) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert decide_temporal_campaign(records).decision is ScientificDecision.BOUNDARY_RESULT


def test_opposite_temporal_movement_is_preserved() -> None:
    records = tuple(_recovery(seed.value, 0.30, 0.10, 0.20) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert records[0].interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
    assert decide_temporal_campaign(records).decision is ScientificDecision.OPPOSITE_DIRECTION


def test_mixed_seed_interpretations_are_boundary() -> None:
    seeds = BOUNDED_EVIDENCE_SEED_COHORT.values
    material = tuple(_recovery(seed.value, 0.10, 0.30, 0.12) for seed in seeds[:5])
    weak = tuple(_recovery(seed.value, 0.10, 0.30, 0.25) for seed in seeds[5:])
    records = material + weak
    assert decide_temporal_campaign(records).decision is ScientificDecision.BOUNDARY_RESULT


def test_full_material_recovery_cohort_is_supported() -> None:
    records = tuple(_recovery(seed.value, 0.10, 0.30, 0.15) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    assert all(
        record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_MATERIAL_RECOVERY
        for record in records
    )
    assert decide_temporal_campaign(records).decision is ScientificDecision.SUPPORTED


def test_mixed_method_campaign_is_blocked() -> None:
    left = _recovery(1, 0.1, 0.3, 0.15, method=FederatedThresholdMethod.LOCAL_THRESHOLD)
    right = _recovery(1, 0.1, 0.3, 0.15, method=FederatedThresholdMethod.SHARED_THRESHOLD)
    decision = decide_temporal_campaign((left, right))
    assert decision.decision is ScientificDecision.BLOCKED


def test_cloned_provenance_across_seeds_is_blocked() -> None:
    shared = _seed_provenance(0)
    records = tuple(
        temporal_recovery(
            seed=seed,
            experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            static_reference_cv=MetricValue(0.10),
            frozen_future_cv=MetricValue(0.30),
            recalibrated_future_cv=MetricValue(0.12),
            provenance=TemporalSeedProvenance(
                seed=seed,
                experiment=shared.experiment,
                population=shared.population,
                threshold_method=shared.threshold_method,
                static_reference=shared.static_reference,
                frozen_future=shared.frozen_future,
                recalibrated_future=shared.recalibrated_future,
                static_threshold_checksum=shared.static_threshold_checksum,
                frozen_threshold_checksum=shared.frozen_threshold_checksum,
                recalibrated_threshold_checksum=shared.recalibrated_threshold_checksum,
                static_evaluation_checksum=shared.static_evaluation_checksum,
                frozen_evaluation_checksum=shared.frozen_evaluation_checksum,
                recalibrated_evaluation_checksum=shared.recalibrated_evaluation_checksum,
                client_inventory_checksum=shared.client_inventory_checksum,
                eligibility_checksum=shared.eligibility_checksum,
                source_row_checksum=shared.source_row_checksum,
                row_order_checksum=shared.row_order_checksum,
            ),
            decision_protocol=_TEST_TEMPORAL_DECISION_PROTOCOL,
        )
        for seed in BOUNDED_EVIDENCE_SEED_COHORT.values
    )
    assert decide_temporal_campaign(records).decision is ScientificDecision.BLOCKED
    assert "cloned" in decide_temporal_campaign(records).rationale


def test_provenance_seed_mismatch_is_rejected() -> None:
    provenance = _seed_provenance(99)
    with pytest.raises(ValueError, match="provenance seed must match"):
        temporal_recovery(
            seed=Seed(0),
            experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            static_reference_cv=MetricValue(0.10),
            frozen_future_cv=MetricValue(0.30),
            recalibrated_future_cv=MetricValue(0.12),
            provenance=provenance,
            decision_protocol=_TEST_TEMPORAL_DECISION_PROTOCOL,
        )


def test_partial_provenance_is_rejected() -> None:
    partial: dict[str, Seed | ExperimentId | PopulationId | FederatedThresholdMethod] = {
        "seed": Seed(0),
        "experiment": ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        "population": PopulationId.EDGE_TEMPORAL_GROUPS,
        "threshold_method": FederatedThresholdMethod.LOCAL_THRESHOLD,
    }
    with pytest.raises(ValidationError):
        TemporalSeedProvenance.model_validate(partial)


def test_primitive_population_provenance_is_rejected() -> None:
    base = _seed_provenance(0)
    with pytest.raises(ValidationError):
        TemporalSeedProvenance(
            seed=base.seed,
            experiment=base.experiment,
            population=PopulationId.EDGE_TEMPORAL_GROUPS.value,  # type: ignore[arg-type]
            threshold_method=base.threshold_method,
            static_reference=base.static_reference,
            frozen_future=base.frozen_future,
            recalibrated_future=base.recalibrated_future,
            static_threshold_checksum=base.static_threshold_checksum,
            frozen_threshold_checksum=base.frozen_threshold_checksum,
            recalibrated_threshold_checksum=base.recalibrated_threshold_checksum,
            static_evaluation_checksum=base.static_evaluation_checksum,
            frozen_evaluation_checksum=base.frozen_evaluation_checksum,
            recalibrated_evaluation_checksum=base.recalibrated_evaluation_checksum,
            client_inventory_checksum=base.client_inventory_checksum,
            eligibility_checksum=base.eligibility_checksum,
            source_row_checksum=base.source_row_checksum,
            row_order_checksum=base.row_order_checksum,
        )


def test_client_trajectories_attach_to_recovery() -> None:
    trajectories = (
        TemporalClientTrajectory(
            seed=Seed(0),
            client=ClientIdentity(
                PopulationId.EDGE_TEMPORAL_GROUPS,
                "client-a",
                PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
            ),
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            eligible=True,
            exclusion_reason=None,
            threshold_static=MetricValue(0.1),
            threshold_frozen=MetricValue(0.2),
            threshold_recalibrated=MetricValue(0.15),
            fpr_static=MetricValue(0.05),
            fpr_frozen=MetricValue(0.20),
            fpr_recalibrated=MetricValue(0.08),
            tpr_static=MetricValue(0.90),
            tpr_frozen=MetricValue(0.85),
            tpr_recalibrated=MetricValue(0.88),
            balanced_accuracy_static=MetricValue(0.92),
            balanced_accuracy_frozen=MetricValue(0.82),
            balanced_accuracy_recalibrated=MetricValue(0.90),
            macro_f1_static=MetricValue(0.91),
            macro_f1_frozen=MetricValue(0.80),
            macro_f1_recalibrated=MetricValue(0.89),
        ),
    )
    result = temporal_recovery(
        seed=Seed(0),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.30),
        recalibrated_future_cv=MetricValue(0.12),
        provenance=_seed_provenance(0),
        decision_protocol=_TEST_TEMPORAL_DECISION_PROTOCOL,
        client_trajectories=trajectories,
    )
    assert len(result.client_trajectories) == 1
    trajectory = result.client_trajectories[0]
    assert trajectory.client_id == "client-a"
    assert trajectory.threshold_movement_frozen is not None
    assert trajectory.threshold_movement_frozen.value == pytest.approx(0.1)
    assert trajectory.fpr_movement_recalibrated is not None
    assert trajectory.fpr_movement_recalibrated.value == pytest.approx(-0.12)


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
        provenance=_seed_provenance(seed, method=method),
        decision_protocol=_TEST_TEMPORAL_DECISION_PROTOCOL,
    )


def _seed_provenance(
    seed: int,
    *,
    method: FederatedThresholdMethod = FederatedThresholdMethod.LOCAL_THRESHOLD,
) -> TemporalSeedProvenance:
    index = seed + 1
    detector = Checksum("a" * 64)
    preprocess = Checksum("b" * 64)
    coordinate = Checksum("c" * 64)
    future_eval = _checksum("d", index)
    future_split = _checksum("e", index)
    static = TemporalDeploymentProvenance(
        state=TemporalState.STATIC_REFERENCE,
        split_protocol=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
        calibration_role=PartitionRole.CALIBRATION,
        evaluation_role=PartitionRole.EVALUATION,
        coordinate_checksum=coordinate,
        checkpoint_checksum=detector,
        preprocessing_state_set_checksum=preprocess,
        split_manifest_checksum=_checksum("1", index),
        calibration_score_set_checksum=_checksum("2", index),
        evaluation_score_set_checksum=_checksum("3", index),
    )
    frozen = TemporalDeploymentProvenance(
        state=TemporalState.FROZEN_FUTURE,
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        calibration_role=PartitionRole.CALIBRATION,
        evaluation_role=PartitionRole.EVALUATION,
        coordinate_checksum=coordinate,
        checkpoint_checksum=detector,
        preprocessing_state_set_checksum=preprocess,
        split_manifest_checksum=future_split,
        calibration_score_set_checksum=_checksum("4", index),
        evaluation_score_set_checksum=future_eval,
    )
    recalibrated = TemporalDeploymentProvenance(
        state=TemporalState.RECALIBRATED_FUTURE,
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        calibration_role=PartitionRole.FUTURE_RECALIBRATION,
        evaluation_role=PartitionRole.EVALUATION,
        coordinate_checksum=coordinate,
        checkpoint_checksum=detector,
        preprocessing_state_set_checksum=preprocess,
        split_manifest_checksum=future_split,
        calibration_score_set_checksum=_checksum("5", index),
        evaluation_score_set_checksum=future_eval,
    )
    return TemporalSeedProvenance(
        seed=Seed(seed),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        threshold_method=method,
        static_reference=static,
        frozen_future=frozen,
        recalibrated_future=recalibrated,
        static_threshold_checksum=_checksum("6", index),
        frozen_threshold_checksum=_checksum("7", index),
        recalibrated_threshold_checksum=_checksum("8", index),
        static_evaluation_checksum=_checksum("9", index),
        frozen_evaluation_checksum=_checksum("0", index),
        recalibrated_evaluation_checksum=_checksum("f", index),
        client_inventory_checksum=_checksum("a1", index),
        eligibility_checksum=_checksum("a2", index),
        source_row_checksum=_checksum("a3", index),
        row_order_checksum=_checksum("a4", index),
        excluded_clients=(),
        unavailable_reasons=(),
    )


def _checksum(prefix: str, index: int) -> Checksum:
    body = f"{prefix}{index:02x}"
    return Checksum((body + "0" * 64)[:64])
