from dataclasses import dataclass

from datp_core.application.ports.learning import CentralizedTrainingRunResult
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.errors import CheckpointSelectionError
from datp_core.domain.learning.checkpoints import (
    AnchorCheckpointTerminationPolicy,
    AnchorTerminationCheckpointResult,
    AnchorTerminationReason,
    CheckpointCandidateResult,
    CheckpointSelectionResult,
    CheckpointSelectionSpec,
    TieBreakEvidence,
)
from datp_core.domain.runtime.seeds import RoundNumber


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


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCheckpointTerminationEvidence:
    terminal_round: RoundNumber
    termination_reason: AnchorTerminationReason


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCheckpointTerminationRequest:
    policy: AnchorCheckpointTerminationPolicy
    evidence: AnchorCheckpointTerminationEvidence


class AnchorCheckpointSelector:
    def select(self, request: AnchorCheckpointTerminationRequest) -> AnchorTerminationCheckpointResult:
        _validated_anchor_termination_evidence(request)
        return AnchorTerminationCheckpointResult(
            selected_round=request.evidence.terminal_round,
            termination_reason=request.evidence.termination_reason,
            prohibited_input_attestation=True,
        )


def _validated_anchor_termination_evidence(request: AnchorCheckpointTerminationRequest) -> None:
    round_value = request.evidence.terminal_round.value
    rounds_max = request.policy.rounds_max.value
    rounds_initial = request.policy.rounds_initial.value
    if round_value > rounds_max:
        raise CheckpointSelectionError(
            detail="anchor checkpoint terminal round cannot exceed the locked anchor round budget",
            candidate_evidence=repr(round_value),
            prohibited_input="terminal round beyond the locked anchor rounds_max",
        )
    if (
        request.evidence.termination_reason is AnchorTerminationReason.ROUND_BUDGET_EXHAUSTED
        and round_value != rounds_max
    ):
        raise CheckpointSelectionError(
            detail="round-budget-exhausted termination must occur exactly at the locked round cap",
            candidate_evidence=repr(round_value),
            prohibited_input="round-budget-exhausted reason claimed at a non-terminal round",
        )
    if request.evidence.termination_reason is AnchorTerminationReason.CONVERGED and round_value < rounds_initial:
        raise CheckpointSelectionError(
            detail="convergence termination cannot occur before the locked initial-round threshold",
            candidate_evidence=repr(round_value),
            prohibited_input="convergence claimed before the locked anchor rounds_initial",
        )


def select_centralized_checkpoint(result: CentralizedTrainingRunResult) -> CentralizedTrainingRunResult:
    # One run per seed, no schedule to rank; only artifact_type isn't already constructor-checked.
    if result.checkpoint_artifact.artifact_type is not ArtifactType.SCIENTIFIC_CHECKPOINT:
        raise CheckpointSelectionError(
            detail="B0 checkpoint selection requires a scientific checkpoint artifact reference",
            candidate_evidence=repr(result.checkpoint_artifact),
            prohibited_input="non-scientific-checkpoint artifact",
        )
    return result
