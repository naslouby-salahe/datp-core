from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from re import fullmatch
from typing import assert_never

from datp_core.domain.artifacts.lineage import (
    CheckpointSelectionIdentity,
    RecoveryCompatibilityIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    CONTENT_HASH_PATTERN,
    ArtifactRef,
    ArtifactSchemaVersion,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.runtime.seeds import RoundNumber, Seed

SCHEDULED_CHECKPOINT_ROUNDS = (25, 50, 75, 100, 125, 150, 200)
REGIME_A_SELECTION_RULE_VERSION = "regime_a_weighted_benign_validation_loss_v1"
EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE = "earliest_scheduled_round_v1"
ANCHOR_CHECKPOINT_ROUNDS_INITIAL = 40
ANCHOR_CHECKPOINT_ROUNDS_MAX = 150


class CheckpointKind(StrEnum):
    SCIENTIFIC = "scientific"
    RECOVERY = "recovery"


class CheckpointProtocol(StrEnum):
    JOURNAL_SCHEDULED = "journal_scheduled"
    ANCHOR_TERMINATION = "anchor_termination"


class CheckpointSelectionStrategy(StrEnum):
    REGIME_A_GLOBAL_PRIMARY = "regime_a_global_primary"


class AnchorTerminationReason(StrEnum):
    CONVERGED = "converged"
    ROUND_BUDGET_EXHAUSTED = "round_budget_exhausted"


class RecoveryCadence(StrEnum):
    COMPLETED_ROUND = "completed_round"
    ELAPSED_TIME = "elapsed_time"


def _validated_rounds(*, rounds: tuple[RoundNumber, ...], name: str) -> None:
    if type(rounds) is not tuple or any(type(round_) is not RoundNumber for round_ in rounds):
        raise DomainValidationError(
            detail=f"{name} must contain typed rounds",
            value=repr(rounds),
            constraint="tuple[RoundNumber, ...]",
        )
    if tuple(round_.value for round_ in rounds) != SCHEDULED_CHECKPOINT_ROUNDS:
        raise DomainValidationError(
            detail=f"{name} must equal the locked checkpoint schedule",
            value=repr(rounds),
            constraint=repr(SCHEDULED_CHECKPOINT_ROUNDS),
        )


def _validated_anchor_policy_round(*, value: RoundNumber, expected: int, name: str) -> None:
    if type(value) is not RoundNumber or value.value != expected:
        raise DomainValidationError(
            detail=f"{name} must equal its locked recovered anchor value",
            value=repr(value),
            constraint=repr(expected),
        )


def _validated_version(*, value: str, expected: str, name: str) -> None:
    if value != expected:
        raise DomainValidationError(
            detail=f"{name} must equal its locked version",
            value=repr(value),
            constraint=expected,
        )


def _validated_content_hash(*, value: str) -> None:
    if fullmatch(CONTENT_HASH_PATTERN, value) is None:
        raise DomainValidationError(
            detail="checkpoint content hash must be a canonical digest",
            value=repr(value),
            constraint=CONTENT_HASH_PATTERN,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSchedule:
    rounds: tuple[RoundNumber, ...]

    def __post_init__(self) -> None:
        _validated_rounds(rounds=self.rounds, name="checkpoint schedule rounds")


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionSpec:
    strategy: CheckpointSelectionStrategy
    candidate_rounds: tuple[RoundNumber, ...]
    selection_rule_version: str
    tie_break_rule: str

    def __post_init__(self) -> None:
        if self.strategy is not CheckpointSelectionStrategy.REGIME_A_GLOBAL_PRIMARY:
            raise DomainValidationError(
                detail="checkpoint selection must use the Regime-A global-primary strategy",
                value=repr(self.strategy),
                constraint="REGIME_A_GLOBAL_PRIMARY",
            )
        _validated_rounds(rounds=self.candidate_rounds, name="checkpoint candidate rounds")
        _validated_version(
            value=self.selection_rule_version,
            expected=REGIME_A_SELECTION_RULE_VERSION,
            name="checkpoint selection rule version",
        )
        _validated_version(
            value=self.tie_break_rule,
            expected=EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
            name="checkpoint tie-break rule",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCheckpointTerminationPolicy:
    rounds_initial: RoundNumber
    rounds_max: RoundNumber

    def __post_init__(self) -> None:
        _validated_anchor_policy_round(
            value=self.rounds_initial, expected=ANCHOR_CHECKPOINT_ROUNDS_INITIAL, name="anchor rounds_initial"
        )
        _validated_anchor_policy_round(
            value=self.rounds_max, expected=ANCHOR_CHECKPOINT_ROUNDS_MAX, name="anchor rounds_max"
        )


LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY = AnchorCheckpointTerminationPolicy(
    rounds_initial=RoundNumber(value=ANCHOR_CHECKPOINT_ROUNDS_INITIAL),
    rounds_max=RoundNumber(value=ANCHOR_CHECKPOINT_ROUNDS_MAX),
)


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeASelectionDiagnostics:
    weighted_benign_validation_reconstruction_mse: float

    def __post_init__(self) -> None:
        if (
            type(self.weighted_benign_validation_reconstruction_mse) is not float
            or not isfinite(self.weighted_benign_validation_reconstruction_mse)
            or self.weighted_benign_validation_reconstruction_mse < 0.0
        ):
            raise DomainValidationError(
                detail="Regime-A weighted benign validation reconstruction MSE must be finite and non-negative",
                value=repr(self.weighted_benign_validation_reconstruction_mse),
                constraint="finite value >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointCandidateResult:
    round: RoundNumber
    regime_a_evidence_identity: StageFingerprint
    allowed_diagnostics: RegimeASelectionDiagnostics
    accepted: bool
    rejection_reason: str | None

    def __post_init__(self) -> None:
        if not _is_valid_checkpoint_candidate(self):
            raise DomainValidationError(
                detail="checkpoint candidate requires scheduled typed evidence and a coherent verdict",
                value=repr(self),
                constraint="scheduled round, typed evidence, and verdict-specific rejection reason",
            )


def _is_valid_checkpoint_candidate(candidate: CheckpointCandidateResult) -> bool:
    return all(
        (
            _is_scheduled_round(candidate.round),
            type(candidate.regime_a_evidence_identity) is StageFingerprint,
            type(candidate.allowed_diagnostics) is RegimeASelectionDiagnostics,
            _has_coherent_candidate_verdict(candidate),
        )
    )


def _is_scheduled_round(round_: RoundNumber) -> bool:
    return type(round_) is RoundNumber and round_.value in SCHEDULED_CHECKPOINT_ROUNDS


def _has_coherent_candidate_verdict(candidate: CheckpointCandidateResult) -> bool:
    if type(candidate.accepted) is not bool:
        return False
    if candidate.accepted:
        return candidate.rejection_reason is None
    return type(candidate.rejection_reason) is str and bool(candidate.rejection_reason)


@dataclass(frozen=True, slots=True, kw_only=True)
class TieBreakEvidence:
    tied_rounds: tuple[RoundNumber, ...]
    selected_round: RoundNumber

    def __post_init__(self) -> None:
        if not _has_typed_tie_break_rounds(self):
            raise DomainValidationError(
                detail="tie-break evidence requires scheduled candidate rounds",
                value=repr(self.tied_rounds),
                constraint="non-empty tuple of scheduled rounds",
            )
        if not all(_is_scheduled_round(round_) for round_ in self.tied_rounds):
            raise DomainValidationError(
                detail="tie-break evidence may contain only scheduled rounds",
                value=repr(self.tied_rounds),
                constraint=repr(SCHEDULED_CHECKPOINT_ROUNDS),
            )
        if not _selects_earliest_distinct_tied_round(self):
            raise DomainValidationError(
                detail="tie-break evidence must select the earliest distinct scheduled round",
                value=repr(self),
                constraint="selected_round == earliest tied round",
            )


def _has_typed_tie_break_rounds(evidence: TieBreakEvidence) -> bool:
    return (
        type(evidence.tied_rounds) is tuple
        and bool(evidence.tied_rounds)
        and type(evidence.selected_round) is RoundNumber
    )


def _selects_earliest_distinct_tied_round(evidence: TieBreakEvidence) -> bool:
    values = tuple(round_.value for round_ in evidence.tied_rounds)
    return len(set(values)) == len(values) and evidence.selected_round.value == min(values)


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionResult:
    all_candidates: tuple[CheckpointCandidateResult, ...]
    selected_round: RoundNumber
    rejected_candidates: tuple[CheckpointCandidateResult, ...]
    tie_break_evidence: TieBreakEvidence
    prohibited_input_attestation: bool

    def __post_init__(self) -> None:
        if not _is_valid_checkpoint_selection(self):
            raise DomainValidationError(
                detail="checkpoint selection requires a complete coherent typed candidate decision record",
                value=repr(self),
                constraint="typed candidates, accepted selection, complete rejection record, tie-break, attestation",
            )


def _is_valid_checkpoint_selection(selection: CheckpointSelectionResult) -> bool:
    return all(
        (
            _has_typed_checkpoint_candidates(selection.all_candidates),
            _has_typed_rejected_candidates(selection.rejected_candidates),
            type(selection.selected_round) is RoundNumber,
            type(selection.tie_break_evidence) is TieBreakEvidence,
            _has_distinct_candidate_rounds(selection.all_candidates),
            _is_accepted_selected_round(selection),
            _has_complete_rejected_candidates(selection),
            _has_matching_tie_break_round(selection),
            selection.prohibited_input_attestation is True,
        )
    )


def _has_typed_checkpoint_candidates(candidates: tuple[CheckpointCandidateResult, ...]) -> bool:
    return (
        type(candidates) is tuple
        and bool(candidates)
        and all(type(candidate) is CheckpointCandidateResult for candidate in candidates)
    )


def _has_typed_rejected_candidates(candidates: tuple[CheckpointCandidateResult, ...]) -> bool:
    return type(candidates) is tuple and all(type(candidate) is CheckpointCandidateResult for candidate in candidates)


def _has_distinct_candidate_rounds(candidates: tuple[CheckpointCandidateResult, ...]) -> bool:
    rounds = tuple(candidate.round for candidate in candidates)
    return len(set(rounds)) == len(rounds)


def _is_accepted_selected_round(selection: CheckpointSelectionResult) -> bool:
    return selection.selected_round in tuple(
        candidate.round for candidate in selection.all_candidates if candidate.accepted
    )


def _has_complete_rejected_candidates(selection: CheckpointSelectionResult) -> bool:
    return selection.rejected_candidates == tuple(
        candidate for candidate in selection.all_candidates if not candidate.accepted
    )


def _has_matching_tie_break_round(selection: CheckpointSelectionResult) -> bool:
    return selection.tie_break_evidence.selected_round == selection.selected_round


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionArtifact:
    selection_identity: CheckpointSelectionIdentity
    result: CheckpointSelectionResult
    content_hash: str
    schema_version: ArtifactSchemaVersion

    def __post_init__(self) -> None:
        if (
            type(self.selection_identity) is not CheckpointSelectionIdentity
            or type(self.result) is not CheckpointSelectionResult
        ):
            raise DomainValidationError(
                detail="checkpoint selection artifact requires typed identity and result",
                value=repr(self),
                constraint="CheckpointSelectionIdentity and CheckpointSelectionResult",
            )
        _validated_content_hash(value=self.content_hash)
        if type(self.schema_version) is not ArtifactSchemaVersion:
            raise DomainValidationError(
                detail="checkpoint selection artifact requires a typed schema version",
                value=repr(self.schema_version),
                constraint="ArtifactSchemaVersion",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorTerminationCheckpointResult:
    selected_round: RoundNumber
    termination_reason: AnchorTerminationReason
    prohibited_input_attestation: bool

    def __post_init__(self) -> None:
        if not _is_valid_anchor_termination_result(self):
            raise DomainValidationError(
                detail="anchor termination checkpoint result requires a typed round, reason, and attestation",
                value=repr(self),
                constraint="RoundNumber, AnchorTerminationReason, prohibited_input_attestation is True",
            )


def _is_valid_anchor_termination_result(result: AnchorTerminationCheckpointResult) -> bool:
    return (
        type(result.selected_round) is RoundNumber
        and type(result.termination_reason) is AnchorTerminationReason
        and result.prohibited_input_attestation is True
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCheckpointSelectionArtifact:
    selection_identity: CheckpointSelectionIdentity
    result: AnchorTerminationCheckpointResult
    content_hash: str
    schema_version: ArtifactSchemaVersion

    def __post_init__(self) -> None:
        if (
            type(self.selection_identity) is not CheckpointSelectionIdentity
            or type(self.result) is not AnchorTerminationCheckpointResult
        ):
            raise DomainValidationError(
                detail="anchor checkpoint selection artifact requires typed identity and result",
                value=repr(self),
                constraint="CheckpointSelectionIdentity and AnchorTerminationCheckpointResult",
            )
        _validated_content_hash(value=self.content_hash)
        if type(self.schema_version) is not ArtifactSchemaVersion:
            raise DomainValidationError(
                detail="anchor checkpoint selection artifact requires a typed schema version",
                value=repr(self.schema_version),
                constraint="ArtifactSchemaVersion",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointDescriptor:
    checkpoint_id: CheckpointId
    round: RoundNumber
    seed: Seed
    training_identity: TrainingIdentity
    protocol: CheckpointProtocol
    artifact_ref: ArtifactRef
    content_hash: str
    schema_version: ArtifactSchemaVersion
    kind: CheckpointKind = field(default=CheckpointKind.SCIENTIFIC, init=False)

    def __post_init__(self) -> None:
        if not _is_valid_checkpoint_descriptor(self):
            raise DomainValidationError(
                detail="scientific checkpoint descriptor requires typed protocol-consistent integrity-bound contents",
                value=repr(self),
                constraint="typed scientific checkpoint with matching artifact integrity metadata",
            )


def _is_valid_checkpoint_descriptor(descriptor: CheckpointDescriptor) -> bool:
    return all(
        (
            _has_checkpoint_descriptor_identity_types(descriptor),
            _is_valid_checkpoint_round(round_=descriptor.round, protocol=descriptor.protocol),
            _has_scientific_checkpoint_artifact(descriptor.artifact_ref),
            _is_valid_content_hash(descriptor.content_hash),
            _has_matching_descriptor_integrity(descriptor),
        )
    )


def _has_checkpoint_descriptor_identity_types(descriptor: CheckpointDescriptor) -> bool:
    return all(
        (
            type(descriptor.checkpoint_id) is CheckpointId,
            type(descriptor.round) is RoundNumber,
            type(descriptor.seed) is Seed,
            type(descriptor.training_identity) is TrainingIdentity,
            type(descriptor.protocol) is CheckpointProtocol,
            type(descriptor.schema_version) is ArtifactSchemaVersion,
        )
    )


def _is_valid_checkpoint_round(*, round_: RoundNumber, protocol: CheckpointProtocol) -> bool:
    if type(round_) is not RoundNumber:
        return False
    if protocol is CheckpointProtocol.JOURNAL_SCHEDULED:
        return _is_scheduled_round(round_)
    if protocol is CheckpointProtocol.ANCHOR_TERMINATION:
        return 1 <= round_.value <= ANCHOR_CHECKPOINT_ROUNDS_MAX
    assert_never(protocol)


def _has_scientific_checkpoint_artifact(artifact_ref: ArtifactRef) -> bool:
    return type(artifact_ref) is ArtifactRef and artifact_ref.artifact_type is ArtifactType.SCIENTIFIC_CHECKPOINT


def _is_valid_content_hash(value: str) -> bool:
    return fullmatch(CONTENT_HASH_PATTERN, value) is not None


def _has_matching_descriptor_integrity(descriptor: CheckpointDescriptor) -> bool:
    return (
        descriptor.content_hash == descriptor.artifact_ref.content_hash
        and descriptor.schema_version == descriptor.artifact_ref.schema_version
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryCheckpointPolicy:
    cadence: RecoveryCadence
    cadence_interval: int
    retention: int
    compatibility_identity: RecoveryCompatibilityIdentity
    atomic_commit: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if not _is_valid_recovery_checkpoint_policy(self):
            raise DomainValidationError(
                detail="recovery policy requires typed cadence, positive limits, and compatibility identity",
                value=repr(self),
                constraint="RecoveryCadence, positive interval and retention, RecoveryCompatibilityIdentity",
            )


def _is_valid_recovery_checkpoint_policy(policy: RecoveryCheckpointPolicy) -> bool:
    return all(
        (
            type(policy.cadence) is RecoveryCadence,
            _is_positive_integer(policy.cadence_interval),
            _is_positive_integer(policy.retention),
            type(policy.compatibility_identity) is RecoveryCompatibilityIdentity,
        )
    )


def _is_positive_integer(value: int) -> bool:
    return type(value) is int and value >= 1


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryState:
    model_state_ref: ArtifactRef
    optimizer_state_ref: ArtifactRef
    scheduler_state_ref: ArtifactRef
    federation_state_ref: ArtifactRef
    rng_state_ref: ArtifactRef
    last_completed_round: RoundNumber
    compatibility_identity: RecoveryCompatibilityIdentity
    kind: CheckpointKind = field(default=CheckpointKind.RECOVERY, init=False)

    def __post_init__(self) -> None:
        state_references = (
            self.model_state_ref,
            self.optimizer_state_ref,
            self.scheduler_state_ref,
            self.federation_state_ref,
            self.rng_state_ref,
        )
        if any(type(reference) is not ArtifactRef for reference in state_references):
            raise DomainValidationError(
                detail="recovery state requires typed model, optimizer, scheduler, federation, and RNG references",
                value=repr(state_references),
                constraint="ArtifactRef for every recovery state reference",
            )
        if type(self.last_completed_round) is not RoundNumber:
            raise DomainValidationError(
                detail="recovery state requires a completed RoundNumber",
                value=repr(self.last_completed_round),
                constraint="RoundNumber",
            )
        if type(self.compatibility_identity) is not RecoveryCompatibilityIdentity:
            raise DomainValidationError(
                detail="recovery state requires a typed compatibility identity",
                value=repr(self.compatibility_identity),
                constraint="RecoveryCompatibilityIdentity",
            )
