"""Temporal smoke outcomes must reflect what every seed completed, not a union.

A method completed by one temporal seed but unavailable in another must not be
surfaced COMPLETED; the dispatch outcome is the intersection across seeds, with
any unavailability surfaced as UNAVAILABLE instead of being absorbed.
"""

from datp_core.analysis.temporal import TemporalRecoveryResult, temporal_recovery
from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TemporalState,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.pipeline.workflows import campaign
from datp_core.pipeline.workflows.temporal import (
    TemporalMethodRecovery,
    TemporalMethodUnavailability,
    TemporalSeedProvenance,
    TemporalSeedResult,
    TemporalStateResult,
)
from datp_core.protocols.temporal import TemporalDeploymentProvenance, temporal_partition_roles, temporal_split_protocol
from datp_core.thresholding.identities import ThresholdInfeasibilityReason

_SHARED = FederatedThresholdMethod.SHARED_THRESHOLD
_LOCAL = FederatedThresholdMethod.LOCAL_THRESHOLD


def _checksum(prefix: str, index: int) -> Checksum:
    body = f"{prefix}{index:02x}"
    return Checksum((body + "0" * 64)[:64])


def _state_provenance(index: int, state: TemporalState) -> TemporalDeploymentProvenance:
    calibration_role, evaluation_role = temporal_partition_roles(state)
    future = state is not TemporalState.STATIC_REFERENCE
    return TemporalDeploymentProvenance(
        state=state,
        split_protocol=temporal_split_protocol(state),
        calibration_role=calibration_role,
        evaluation_role=evaluation_role,
        coordinate_checksum=_checksum("c", index),
        checkpoint_checksum=_checksum("a", index),
        preprocessing_state_set_checksum=_checksum("b", index),
        split_manifest_checksum=_checksum("e", index) if future else _checksum("1", index),
        calibration_score_set_checksum=_checksum("4", index) if future else _checksum("2", index),
        evaluation_score_set_checksum=_checksum("d", index) if future else _checksum("3", index),
    )


def _seed_provenance(index: int, method: FederatedThresholdMethod = _SHARED) -> TemporalSeedProvenance:
    return TemporalSeedProvenance(
        seed=Seed(index),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS.value,
        threshold_method=method,
        static_reference=_state_provenance(index, TemporalState.STATIC_REFERENCE),
        frozen_future=_state_provenance(index, TemporalState.FROZEN_FUTURE),
        recalibrated_future=_state_provenance(index, TemporalState.RECALIBRATED_FUTURE),
        static_threshold_checksum=_checksum("6", index),
        frozen_threshold_checksum=_checksum("7", index),
        recalibrated_threshold_checksum=_checksum("8", index),
        static_evaluation_checksum=_checksum("9", index),
        frozen_evaluation_checksum=_checksum("0", index),
        recalibrated_evaluation_checksum=_checksum("f", index),
        client_inventory_checksum=_checksum("g", index),
        eligibility_checksum=_checksum("h", index),
        source_row_checksum=_checksum("i", index),
        row_order_checksum=_checksum("j", index),
    )


def _recovery(index: int, method: FederatedThresholdMethod) -> TemporalRecoveryResult:
    return temporal_recovery(
        seed=Seed(index),
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        threshold_method=method,
        static_reference_cv=MetricValue(1.0),
        frozen_future_cv=MetricValue(1.0),
        recalibrated_future_cv=MetricValue(1.0),
        provenance=_seed_provenance(index, method=method),
    )


def _state(state: TemporalState, index: int, completed, unavailable) -> TemporalStateResult:
    return TemporalStateResult(
        state=state,
        completed_threshold_methods=completed,
        provenance=_state_provenance(index, state),
        outcomes=(),
        unavailable_methods=unavailable,
    )


def _seed(index: int, *, completed, unavailable) -> TemporalSeedResult:
    unavailability = tuple(
        TemporalMethodUnavailability(
            method=method,
            reason=ThresholdInfeasibilityReason.GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION,
            detail="eligibility floor unmet in this partition",
        )
        for method in unavailable
    )
    states = {
        TemporalState.STATIC_REFERENCE: _state(TemporalState.STATIC_REFERENCE, index, completed, unavailability),
        TemporalState.FROZEN_FUTURE: _state(TemporalState.FROZEN_FUTURE, index, completed, unavailability),
        TemporalState.RECALIBRATED_FUTURE: _state(TemporalState.RECALIBRATED_FUTURE, index, completed, unavailability),
    }
    return TemporalSeedResult(
        partition_seed=Seed(index),
        static_reference=states[TemporalState.STATIC_REFERENCE],
        frozen_future=states[TemporalState.FROZEN_FUTURE],
        recalibrated_future=states[TemporalState.RECALIBRATED_FUTURE],
        recoveries=tuple(
            TemporalMethodRecovery(method=method, recovery=_recovery(index, method)) for method in completed
        ),
    )


def test_temporal_outcome_is_the_intersection_across_seeds() -> None:
    complete_both = _seed(1, completed=(_SHARED, _LOCAL), unavailable=())
    partial = _seed(2, completed=(_SHARED,), unavailable=(_LOCAL,))

    outcomes = campaign._temporal_method_outcomes((complete_both, partial))

    by_method = {outcome.method: outcome for outcome in outcomes}
    assert by_method[_SHARED].status.value == "completed"
    assert by_method[_LOCAL].status.value == "unavailable"
    assert "group_count_exceeds_eligible_population" in by_method[_LOCAL].detail


def test_temporal_outcome_marks_all_completed_for_a_full_seed() -> None:
    outcomes = campaign._temporal_method_outcomes((_seed(1, completed=(_SHARED, _LOCAL), unavailable=()),))

    by_method = {outcome.method: outcome for outcome in outcomes}
    assert by_method[_SHARED].status.value == "completed"
    assert by_method[_LOCAL].status.value == "completed"
