from pathlib import Path

import pytest
from datp_core.anchor.gate import (
    assert_gate_not_bypassable,
    decide_anchor_gate,
    dependent_readiness_from_gate,
    load_anchor_confirmatory_handoff,
    load_verified_anchor_gate_artifact,
    persist_anchor_gate_diagnostics,
    validate_handoff_against_confirmatory_programme,
)
from datp_core.anchor.models import (
    AnchorArtifactFileName,
    AnchorGateStatus,
    AnchorObservationSourceKind,
    AnchorObservedMetric,
)
from datp_core.anchor.reproduction import (
    independent_reproduction_dependency_blocker,
    reproduce_anchor,
)
from pydantic import ValidationError as PydanticValidationError
from tests.unit.anchor.helpers import matching_anchor_observations

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import AnchorReproductionError
from datp_core.core.identifiers import EvidenceRole, ExperimentId, ExperimentReadiness, PopulationId
from datp_core.core.numeric import MetricValue


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


def test_verified_anchor_gate_artifact_round_trip(tmp_path: Path) -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    checksum = persist_anchor_gate_diagnostics(decision, tmp_path)
    verified = load_verified_anchor_gate_artifact(tmp_path)
    assert verified.permits_confirmatory_claims
    assert verified.artifact_checksum == checksum
    assert verified.decision.status is AnchorGateStatus.PASS


def test_manual_gate_success_cannot_be_asserted_without_artifact(tmp_path: Path) -> None:
    with pytest.raises(AnchorReproductionError, match="missing"):
        load_verified_anchor_gate_artifact(tmp_path)
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    persist_anchor_gate_diagnostics(decision, tmp_path)
    marker = tmp_path / "anchor_gate_complete.json"
    marker.write_text('{"artifact_checksum":"' + ("0" * 64) + '","status":"pass"}', encoding="utf-8")
    with pytest.raises(AnchorReproductionError, match="stale|mismatched"):
        load_verified_anchor_gate_artifact(tmp_path)


def test_blocked_gate_artifact_cannot_verify_as_passed(tmp_path: Path) -> None:
    decision = decide_anchor_gate(
        reproduce_anchor(
            observations=(),
            dependency_blocker=independent_reproduction_dependency_blocker(),
        )
    )
    assert decision.status is AnchorGateStatus.BLOCKED
    persist_anchor_gate_diagnostics(decision, tmp_path)
    with pytest.raises(AnchorReproductionError):
        load_verified_anchor_gate_artifact(tmp_path)
    assert not (tmp_path / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value).exists()


def test_pass_persists_and_loads_confirmatory_handoff(tmp_path: Path) -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    persist_anchor_gate_diagnostics(decision, tmp_path)
    verified = load_verified_anchor_gate_artifact(tmp_path)
    handoff = load_anchor_confirmatory_handoff(tmp_path, verified_gate=verified)
    assert handoff.dependent_confirmatory_experiment is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION
    assert handoff.dependent_population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert handoff.verified_gate_artifact_checksum == verified.artifact_checksum
    assert handoff.anchor_gate_decision_checksum == verified.artifact_checksum
    assert validate_handoff_against_confirmatory_programme(handoff) is handoff


def test_handoff_missing_fails_closed(tmp_path: Path) -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    persist_anchor_gate_diagnostics(decision, tmp_path)
    verified = load_verified_anchor_gate_artifact(tmp_path)
    (tmp_path / AnchorArtifactFileName.CONFIRMATORY_HANDOFF.value).unlink()
    with pytest.raises(AnchorReproductionError, match="handoff artifact is missing"):
        load_anchor_confirmatory_handoff(tmp_path, verified_gate=verified)


def test_stale_handoff_programme_binding_is_rejected(tmp_path: Path) -> None:
    decision = decide_anchor_gate(reproduce_anchor(observations=matching_anchor_observations()))
    persist_anchor_gate_diagnostics(decision, tmp_path)
    verified = load_verified_anchor_gate_artifact(tmp_path)
    handoff = load_anchor_confirmatory_handoff(tmp_path, verified_gate=verified)
    stale = handoff.model_copy(update={"dependent_population": PopulationId.NBAIOT_DIRICHLET_CLIENTS})
    with pytest.raises(AnchorReproductionError, match="stale relative to the locked confirmatory programme"):
        validate_handoff_against_confirmatory_programme(stale)
