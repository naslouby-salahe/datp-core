import pytest
from tests.unit.anchor.helpers import matching_anchor_observations

from datp_core.anchor.comparison import AnchorObservedMetric
from datp_core.anchor.gate import AnchorGateStatus, decide_anchor_gate, dependent_readiness_from_gate
from datp_core.anchor.reproduction import (
    independent_reproduction_dependency_blocker,
    reproduce_anchor,
    validate_historical_seed_cohort,
)
from datp_core.domain.enums import ExperimentId, ExperimentReadiness
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT


def test_blocked_anchor_prevents_claim_permitted_dependent_readiness() -> None:
    observations = list(matching_anchor_observations())
    first = observations[0]
    observations[0] = AnchorObservedMetric(
        seed=first.seed,
        population=first.population,
        training_model=first.training_model,
        threshold_method=first.threshold_method,
        metric=first.metric,
        value=MetricValue(0.0),
        checkpoint_status=first.checkpoint_status,
        source_kind=first.source_kind,
        artifact_path=first.artifact_path,
        artifact_checksum=first.artifact_checksum,
        model_checkpoint_identity=first.model_checkpoint_identity,
        evidence_role=first.evidence_role,
    )
    decision = decide_anchor_gate(reproduce_anchor(observations=tuple(observations)))
    assert decision.status is AnchorGateStatus.BLOCKED
    assert decision.dependent_readiness is ExperimentReadiness.BLOCKED
    assert dependent_readiness_from_gate(decision) is not ExperimentReadiness.EXECUTABLE
    assert decision.reproduction.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION


def test_dependency_blocker_blocks_dependent_extension_evidence() -> None:
    decision = decide_anchor_gate(
        reproduce_anchor(
            observations=(),
            dependency_blocker=independent_reproduction_dependency_blocker(),
        )
    )
    assert decision.status is AnchorGateStatus.BLOCKED
    assert decision.dependent_readiness is ExperimentReadiness.BLOCKED
    assert decision.reproduction.dependency_blocker is not None


def test_ten_seed_confirmatory_cohort_cannot_become_anchor_evidence() -> None:
    with pytest.raises(AnchorReproductionError, match="ten-seed"):
        validate_historical_seed_cohort(CONFIRMATORY_SEED_COHORT)


def test_pass_does_not_mark_dependent_executable() -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    assert decision.status is AnchorGateStatus.PASS
    assert decision.dependent_readiness is ExperimentReadiness.DECLARED
    assert decision.dependent_readiness is not ExperimentReadiness.EXECUTABLE
