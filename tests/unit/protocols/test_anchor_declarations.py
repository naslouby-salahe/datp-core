from datp_core.protocols.anchor import (
    ANCHOR_DECISION_PROTOCOL,
    HISTORICAL_ANCHOR_SEED_COHORT,
    HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
    HISTORICAL_SHARED_THRESHOLD_CV_FPR,
)
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL

from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE


def test_anchor_references_lock_each_historical_threshold_scope() -> None:
    shared_references = tuple(
        reference
        for reference in ANCHOR_DECISION_PROTOCOL.references
        if reference.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD
    )
    local_references = tuple(
        reference
        for reference in ANCHOR_DECISION_PROTOCOL.references
        if reference.threshold_method is FederatedThresholdMethod.LOCAL_THRESHOLD
    )
    assert ANCHOR_DECISION_PROTOCOL.seed_cohort == HISTORICAL_ANCHOR_SEED_COHORT
    assert HISTORICAL_ANCHOR_SEED_COHORT.member_count.value < CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count.value
    assert all(
        reference.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION for reference in ANCHOR_DECISION_PROTOCOL.references
    )
    assert all(
        reference.absolute_tolerance == NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE
        for reference in ANCHOR_DECISION_PROTOCOL.references
    )

    assert tuple(reference.seed for reference in shared_references) == HISTORICAL_ANCHOR_SEED_COHORT.values
    assert tuple(reference.seed for reference in local_references) == HISTORICAL_ANCHOR_SEED_COHORT.values
    assert tuple(reference.value for reference in shared_references) == HISTORICAL_SHARED_THRESHOLD_CV_FPR
    assert tuple(reference.value for reference in local_references) == HISTORICAL_LOCAL_THRESHOLD_CV_FPR
    assert {reference.threshold_method for reference in shared_references} == {
        FederatedThresholdMethod.SHARED_THRESHOLD
    }
    assert {reference.threshold_method for reference in local_references} == {FederatedThresholdMethod.LOCAL_THRESHOLD}
