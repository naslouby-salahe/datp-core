from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError
from tests.unit.anchor.helpers import matching_anchor_observations

from datp_core.anchor.gate import assert_gate_not_bypassable, decide_anchor_gate, dependent_readiness_from_gate
from datp_core.anchor.models import AnchorGateStatus, AnchorObservationSourceKind, AnchorObservedMetric
from datp_core.anchor.reproduction import independent_reproduction_dependency_blocker, reproduce_anchor
from datp_core.domain.enums import EvidenceRole, ExperimentReadiness
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.ratios import MetricValue


def test_pass_when_all_mandatory_comparisons_match() -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    assert decision.status is AnchorGateStatus.PASS
    assert decision.dependent_readiness is ExperimentReadiness.DECLARED
    assert decision.blocking_discrepancies == ()


def test_blocked_gate_propagates_to_dependent_readiness() -> None:
    observations = list(matching_anchor_observations())
    first = observations[0]
    observations[0] = AnchorObservedMetric(
        seed=first.seed,
        population=first.population,
        training_model=first.training_model,
        threshold_method=first.threshold_method,
        metric=first.metric,
        value=MetricValue(first.value.value + 1.0),
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
    assert dependent_readiness_from_gate(decision) is ExperimentReadiness.BLOCKED
    assert decision.blocking_discrepancies
    assert decision.reproduction.discrepancies


def test_diagnostics_remain_available_when_blocked() -> None:
    decision = decide_anchor_gate(
        reproduce_anchor(
            observations=(),
            dependency_blocker=independent_reproduction_dependency_blocker(),
        )
    )
    assert decision.status is AnchorGateStatus.BLOCKED
    assert decision.reproduction.dependency_blocker is not None
    assert decision.reproduction.discrepancies
    guarded = assert_gate_not_bypassable(decision)
    assert guarded.reproduction.discrepancies == decision.reproduction.discrepancies


def test_caller_cannot_force_executable_dependent_readiness() -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    with pytest.raises(ValueError, match="declared dependent readiness"):
        type(decision)(
            status=AnchorGateStatus.PASS,
            dependent_readiness=ExperimentReadiness.EXECUTABLE,
            reproduction=decision.reproduction,
            blocking_discrepancies=(),
            declared_discrepancies=(),
        )


def test_assert_gate_rejects_blocked_without_diagnostics() -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    with pytest.raises(ValueError):
        type(decision)(
            status=AnchorGateStatus.BLOCKED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            reproduction=decision.reproduction,
            blocking_discrepancies=(),
            declared_discrepancies=(),
        )


def test_no_manual_override_api_on_gate_decision() -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    assert not hasattr(decision, "override")
    assert not hasattr(decision, "force_pass")
    with pytest.raises((AttributeError, PydanticValidationError)):
        decision.__setattr__("status", AnchorGateStatus.BLOCKED)


def test_observation_source_kind_remains_explicit() -> None:
    first = matching_anchor_observations()[0]
    assert first.source_kind is AnchorObservationSourceKind.HISTORICAL_ARTIFACT
    assert first.evidence_role is EvidenceRole.ANCHOR_REPRODUCTION
    assert isinstance(first.artifact_path, Path)
    assert isinstance(first.artifact_checksum, Checksum)
