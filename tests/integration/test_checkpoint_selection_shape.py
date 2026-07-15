from datp_core.domain.artifacts.lineage import CheckpointSelectionIdentity
from datp_core.domain.artifacts.references import ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.learning.checkpoints import (
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
