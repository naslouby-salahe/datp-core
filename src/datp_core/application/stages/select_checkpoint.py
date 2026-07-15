from dataclasses import dataclass

from datp_core.domain.errors import CheckpointSelectionError
from datp_core.domain.learning.checkpoints import (
    CheckpointCandidateResult,
    CheckpointSelectionResult,
    CheckpointSelectionSpec,
    TieBreakEvidence,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionRequest:
    specification: CheckpointSelectionSpec
    candidates: tuple[CheckpointCandidateResult, ...]


class CheckpointSelector:
    def select(self, request: CheckpointSelectionRequest) -> CheckpointSelectionResult:
        candidates = _candidates_in_specification_order(request)
        accepted_candidates = tuple(candidate for candidate in candidates if candidate.accepted)
        best_loss = min(
            candidate.allowed_diagnostics.weighted_benign_validation_reconstruction_mse
            for candidate in accepted_candidates
        )
        tied_rounds = tuple(
            candidate.round
            for candidate in accepted_candidates
            if candidate.allowed_diagnostics.weighted_benign_validation_reconstruction_mse == best_loss
        )
        selected_round = min(tied_rounds, key=lambda candidate_round: candidate_round.value)
        return CheckpointSelectionResult(
            all_candidates=candidates,
            selected_round=selected_round,
            rejected_candidates=tuple(candidate for candidate in candidates if not candidate.accepted),
            tie_break_evidence=TieBreakEvidence(tied_rounds=tied_rounds, selected_round=selected_round),
            prohibited_input_attestation=True,
        )


def _candidates_in_specification_order(request: CheckpointSelectionRequest) -> tuple[CheckpointCandidateResult, ...]:
    candidate_rounds = tuple(candidate.round for candidate in request.candidates)
    if candidate_rounds != request.specification.candidate_rounds:
        raise CheckpointSelectionError(
            detail="checkpoint selection requires exactly one candidate in the locked scheduled order",
            candidate_evidence=repr(candidate_rounds),
            prohibited_input="incomplete, duplicate, reordered, or unscheduled candidate descriptors",
        )
    if not any(candidate.accepted for candidate in request.candidates):
        raise CheckpointSelectionError(
            detail="checkpoint selection requires an accepted scheduled Regime-A candidate",
            candidate_evidence=repr(request.candidates),
            prohibited_input="no accepted Regime-A candidate",
        )
    return request.candidates
