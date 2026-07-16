import pytest

from datp_core.application.stages.select_checkpoint import (
    AnchorCheckpointSelector,
    AnchorCheckpointTerminationEvidence,
    AnchorCheckpointTerminationRequest,
)
from datp_core.domain.artifacts.lineage import CheckpointSelectionIdentity
from datp_core.domain.artifacts.references import ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.errors import CheckpointSelectionError
from datp_core.domain.learning.checkpoints import (
    LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY,
    AnchorCheckpointSelectionArtifact,
    AnchorTerminationReason,
    CheckpointCandidateResult,
    CheckpointSelectionArtifact,
    CheckpointSelectionResult,
    RegimeASelectionDiagnostics,
    TieBreakEvidence,
)
from datp_core.domain.runtime.seeds import RoundNumber


def _synthetic_candidate(
    *, round_value: int, accepted: bool, rejection_reason: str | None
) -> CheckpointCandidateResult:
    return CheckpointCandidateResult(
        round=RoundNumber(value=round_value),
        regime_a_evidence_identity=StageFingerprint(value="a" * 64),
        allowed_diagnostics=RegimeASelectionDiagnostics(weighted_benign_validation_reconstruction_mse=0.5),
        accepted=accepted,
        rejection_reason=rejection_reason,
    )


def _synthetic_selection_artifact() -> CheckpointSelectionArtifact:
    first = _synthetic_candidate(round_value=25, accepted=True, rejection_reason=None)
    second = _synthetic_candidate(round_value=50, accepted=True, rejection_reason=None)
    rejected = _synthetic_candidate(round_value=75, accepted=False, rejection_reason="synthetic rejection")
    result = CheckpointSelectionResult(
        all_candidates=(first, second, rejected),
        selected_round=RoundNumber(value=25),
        rejected_candidates=(rejected,),
        tie_break_evidence=TieBreakEvidence(
            tied_rounds=(RoundNumber(value=25), RoundNumber(value=50)),
            selected_round=RoundNumber(value=25),
        ),
        prohibited_input_attestation=True,
    )
    return CheckpointSelectionArtifact(
        selection_identity=CheckpointSelectionIdentity(value=StageFingerprint(value="b" * 64)),
        result=result,
        content_hash="c" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )


def test_synthetic_selection_shape_is_stable_for_tie_and_rejection() -> None:
    first = _synthetic_selection_artifact()
    second = _synthetic_selection_artifact()

    assert first == second
    assert first.result.selected_round == RoundNumber(value=25)
    assert tuple(candidate.round.value for candidate in first.result.rejected_candidates) == (75,)
    assert tuple(round_.value for round_ in first.result.tie_break_evidence.tied_rounds) == (25, 50)


def _synthetic_anchor_selection_artifact(*, terminal_round: int) -> AnchorCheckpointSelectionArtifact:
    request = AnchorCheckpointTerminationRequest(
        policy=LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY,
        evidence=AnchorCheckpointTerminationEvidence(
            terminal_round=RoundNumber(value=terminal_round),
            termination_reason=AnchorTerminationReason.CONVERGED,
        ),
    )
    result = AnchorCheckpointSelector().select(request)
    return AnchorCheckpointSelectionArtifact(
        selection_identity=CheckpointSelectionIdentity(value=StageFingerprint(value="d" * 64)),
        result=result,
        content_hash="e" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )


def test_anchor_selection_shape_is_stable_for_an_unscheduled_convergence_round() -> None:
    first = _synthetic_anchor_selection_artifact(terminal_round=118)
    second = _synthetic_anchor_selection_artifact(terminal_round=118)

    assert first == second
    assert first.result.selected_round == RoundNumber(value=118)
    assert first.result.termination_reason is AnchorTerminationReason.CONVERGED
    assert first.result.prohibited_input_attestation is True


def test_anchor_selector_accepts_round_budget_exhaustion_only_at_the_locked_cap() -> None:
    request_at_cap = AnchorCheckpointTerminationRequest(
        policy=LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY,
        evidence=AnchorCheckpointTerminationEvidence(
            terminal_round=RoundNumber(value=150),
            termination_reason=AnchorTerminationReason.ROUND_BUDGET_EXHAUSTED,
        ),
    )
    request_before_cap = AnchorCheckpointTerminationRequest(
        policy=LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY,
        evidence=AnchorCheckpointTerminationEvidence(
            terminal_round=RoundNumber(value=149),
            termination_reason=AnchorTerminationReason.ROUND_BUDGET_EXHAUSTED,
        ),
    )
    selector = AnchorCheckpointSelector()

    accepted = selector.select(request_at_cap)

    assert accepted.selected_round == RoundNumber(value=150)
    with pytest.raises(CheckpointSelectionError):
        selector.select(request_before_cap)


def test_anchor_selector_rejects_a_convergence_claim_before_the_locked_initial_round() -> None:
    request = AnchorCheckpointTerminationRequest(
        policy=LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY,
        evidence=AnchorCheckpointTerminationEvidence(
            terminal_round=RoundNumber(value=10),
            termination_reason=AnchorTerminationReason.CONVERGED,
        ),
    )
    selector = AnchorCheckpointSelector()

    with pytest.raises(CheckpointSelectionError):
        selector.select(request)


def test_anchor_selector_rejects_a_terminal_round_beyond_the_locked_round_budget() -> None:
    request = AnchorCheckpointTerminationRequest(
        policy=LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY,
        evidence=AnchorCheckpointTerminationEvidence(
            terminal_round=RoundNumber(value=151),
            termination_reason=AnchorTerminationReason.CONVERGED,
        ),
    )
    selector = AnchorCheckpointSelector()

    with pytest.raises(CheckpointSelectionError):
        selector.select(request)
