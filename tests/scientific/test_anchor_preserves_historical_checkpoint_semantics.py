import pytest
from tests.unit.anchor.helpers import make_observation, make_reference, matching_anchor_observations

from datp_core.core.errors import AnchorReproductionError, ScientificContractError
from datp_core.core.identifiers import CheckpointStatus, FederatedThresholdMethod, MetricId, TrainingModelId
from datp_core.experiments.anchor.contracts import ExactEqualityRule
from datp_core.experiments.anchor.reproduction import (
    ANCHOR_CHECKPOINT_STATUS,
    references_from_protocol,
    reproduce_anchor,
)
from datp_core.experiments.anchor.spec import HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT


def test_references_lock_historical_endpoint_not_selected_candidates() -> None:
    references = references_from_protocol()
    assert all(item.checkpoint_status is CheckpointStatus.HISTORICAL_ENDPOINT for item in references)
    assert CheckpointStatus.SELECTED_BY_NON_TEST_RULE not in {item.checkpoint_status for item in references}
    assert CheckpointStatus.CANDIDATE not in {item.checkpoint_status for item in references}


def test_historical_and_confirmatory_seed_cohorts_remain_structurally_distinct() -> None:
    assert HISTORICAL_ANCHOR_SEED_COHORT.member_count.value == 5
    assert CONFIRMATORY_SEED_COHORT.member_count.value == 10
    assert HISTORICAL_ANCHOR_SEED_COHORT != CONFIRMATORY_SEED_COHORT
    assert set(HISTORICAL_ANCHOR_SEED_COHORT.values).issubset(set(CONFIRMATORY_SEED_COHORT.values))


def test_selected_checkpoint_status_cannot_replace_historical_endpoint() -> None:
    with pytest.raises(ScientificContractError, match="historical endpoint"):
        make_reference(
            rule=ExactEqualityRule(),
            checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        )


def test_observations_with_non_historical_checkpoint_are_rejected_as_cohort() -> None:
    observations = tuple(
        make_observation(
            seed=reference.seed,
            value=reference.value.value,
            threshold_method=reference.threshold_method,
            checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        )
        for reference in references_from_protocol()
    )
    with pytest.raises(AnchorReproductionError, match="checkpoint"):
        reproduce_anchor(observations=observations)


def test_shared_and_local_scopes_remain_paired_under_historical_identity() -> None:
    references = references_from_protocol()
    shared = [item for item in references if item.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD]
    local = [item for item in references if item.threshold_method is FederatedThresholdMethod.LOCAL_THRESHOLD]
    assert [item.seed for item in shared] == list(HISTORICAL_ANCHOR_SEED_COHORT.values)
    assert [item.seed for item in local] == list(HISTORICAL_ANCHOR_SEED_COHORT.values)
    assert all(item.training_model is TrainingModelId.FEDAVG_AUTOENCODER for item in references)
    assert all(item.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION for item in references)
    assert all(item.checkpoint_status is ANCHOR_CHECKPOINT_STATUS for item in references)
    assert len(matching_anchor_observations()) == 10
