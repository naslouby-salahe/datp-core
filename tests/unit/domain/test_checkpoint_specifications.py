from dataclasses import fields

import pytest

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CheckpointSelectionIdentity,
    RecoveryCompatibilityIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.checkpoints import (
    EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
    REGIME_A_SELECTION_RULE_VERSION,
    AnchorCheckpointSelectionArtifact,
    AnchorCheckpointTerminationPolicy,
    AnchorTerminationCheckpointResult,
    AnchorTerminationReason,
    CheckpointCandidateResult,
    CheckpointDescriptor,
    CheckpointProtocol,
    CheckpointSchedule,
    CheckpointSelectionArtifact,
    CheckpointSelectionResult,
    CheckpointSelectionSpec,
    CheckpointSelectionStrategy,
    RecoveryState,
    RegimeASelectionDiagnostics,
    TieBreakEvidence,
)
from datp_core.domain.runtime.seeds import RoundNumber, Seed


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _artifact(*, artifact_type: ArtifactType, character: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.TORCH_STATE,
    )


def _candidate(*, round_value: int, accepted: bool, rejection_reason: str | None) -> CheckpointCandidateResult:
    return CheckpointCandidateResult(
        round=RoundNumber(value=round_value),
        regime_a_evidence_identity=_fingerprint("a"),
        allowed_diagnostics=RegimeASelectionDiagnostics(weighted_benign_validation_reconstruction_mse=0.25),
        accepted=accepted,
        rejection_reason=rejection_reason,
    )


def _selection_result() -> CheckpointSelectionResult:
    first = _candidate(round_value=25, accepted=True, rejection_reason=None)
    second = _candidate(round_value=50, accepted=True, rejection_reason=None)
    rejected = _candidate(round_value=75, accepted=False, rejection_reason="non-finite validation reconstruction")
    return CheckpointSelectionResult(
        all_candidates=(first, second, rejected),
        selected_round=RoundNumber(value=25),
        rejected_candidates=(rejected,),
        tie_break_evidence=TieBreakEvidence(
            tied_rounds=(RoundNumber(value=25), RoundNumber(value=50)),
            selected_round=RoundNumber(value=25),
        ),
        prohibited_input_attestation=True,
    )


_SCHEDULED_CHECKPOINT_ROUNDS = (25, 50, 75, 100, 125, 150, 200)


def test_checkpoint_schedule_and_global_selection_spec_are_locked() -> None:
    schedule = CheckpointSchedule(rounds=tuple(RoundNumber(value=value) for value in _SCHEDULED_CHECKPOINT_ROUNDS))
    specification = CheckpointSelectionSpec(
        strategy=CheckpointSelectionStrategy.REGIME_A_GLOBAL_PRIMARY,
        candidate_rounds=schedule.rounds,
        selection_rule_version=REGIME_A_SELECTION_RULE_VERSION,
        tie_break_rule=EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
    )

    assert tuple(round_.value for round_ in schedule.rounds) == _SCHEDULED_CHECKPOINT_ROUNDS
    assert specification.strategy is CheckpointSelectionStrategy.REGIME_A_GLOBAL_PRIMARY


def test_selection_types_have_no_forbidden_evidence_surface() -> None:
    forbidden_fragments = ("attack", "auroc", "regime_d", "fedprox", "personalization", "poison", "threshold")
    selection_field_names = {
        entry.name for type_ in (CheckpointCandidateResult, CheckpointSelectionResult) for entry in fields(type_)
    }

    assert all(fragment not in name for fragment in forbidden_fragments for name in selection_field_names)


def test_recovery_state_is_distinct_from_scientific_checkpoint_and_selection_artifact() -> None:
    recovery_artifact = _artifact(artifact_type=ArtifactType.RECOVERY_CHECKPOINT, character="b")
    recovery_state = RecoveryState(
        model_state_ref=recovery_artifact,
        optimizer_state_ref=recovery_artifact,
        scheduler_state_ref=recovery_artifact,
        federation_state_ref=recovery_artifact,
        rng_state_ref=recovery_artifact,
        last_completed_round=RoundNumber(value=24),
        compatibility_identity=RecoveryCompatibilityIdentity(value=_fingerprint("c")),
    )
    selection_artifact = CheckpointSelectionArtifact(
        selection_identity=CheckpointSelectionIdentity(value=_fingerprint("d")),
        result=_selection_result(),
        content_hash="e" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )
    checkpoint_descriptor = CheckpointDescriptor(
        checkpoint_id=CheckpointId(value=f"checkpoint-{'f' * 64}"),
        round=RoundNumber(value=25),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=_fingerprint("1")),
        protocol=CheckpointProtocol.COMPLETE_SCHEDULED,
        artifact_ref=_artifact(artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT, character="2"),
        content_hash="2" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )

    assert not isinstance(recovery_state, CheckpointDescriptor)
    assert not isinstance(recovery_state, CheckpointSelectionArtifact)
    assert selection_artifact.result.selected_round == checkpoint_descriptor.round


def test_anchor_termination_policy_validates_typed_positive_ordered_rounds() -> None:
    policy = AnchorCheckpointTerminationPolicy(
        rounds_initial=RoundNumber(value=40),
        rounds_max=RoundNumber(value=150),
    )

    assert policy.rounds_initial.value == 40
    assert policy.rounds_max.value == 150
    with pytest.raises(DomainValidationError):
        AnchorCheckpointTerminationPolicy(rounds_initial=RoundNumber(value=200), rounds_max=RoundNumber(value=150))


def test_anchor_termination_result_rejects_a_false_attestation() -> None:
    selected_round = RoundNumber(value=118)

    with pytest.raises(DomainValidationError):
        AnchorTerminationCheckpointResult(
            selected_round=selected_round,
            termination_reason=AnchorTerminationReason.CONVERGED,
            prohibited_input_attestation=False,
        )


def test_anchor_checkpoint_descriptor_accepts_any_positive_terminal_round() -> None:
    checkpoint_descriptor = CheckpointDescriptor(
        checkpoint_id=CheckpointId(value=f"checkpoint-{'a' * 64}"),
        round=RoundNumber(value=118),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=_fingerprint("2")),
        protocol=CheckpointProtocol.ANCHOR_TERMINATION,
        artifact_ref=_artifact(artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT, character="3"),
        content_hash="3" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )
    checkpoint_id = CheckpointId(value=f"checkpoint-{'b' * 64}")
    seed = Seed(value=1)
    training_identity = TrainingIdentity(value=_fingerprint("4"))
    artifact_ref = _artifact(artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT, character="5")
    schema_version = ArtifactSchemaVersion(value="v1")

    assert checkpoint_descriptor.round.value == 118
    beyond_round_budget = CheckpointDescriptor(
        checkpoint_id=checkpoint_id,
        round=RoundNumber(value=151),
        seed=seed,
        training_identity=training_identity,
        protocol=CheckpointProtocol.ANCHOR_TERMINATION,
        artifact_ref=artifact_ref,
        content_hash="5" * 64,
        schema_version=schema_version,
    )
    assert beyond_round_budget.round.value == 151


def test_anchor_checkpoint_selection_artifact_is_distinct_from_the_complete_artifact() -> None:
    anchor_artifact = AnchorCheckpointSelectionArtifact(
        selection_identity=CheckpointSelectionIdentity(value=_fingerprint("6")),
        result=AnchorTerminationCheckpointResult(
            selected_round=RoundNumber(value=118),
            termination_reason=AnchorTerminationReason.CONVERGED,
            prohibited_input_attestation=True,
        ),
        content_hash="7" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )

    assert not isinstance(anchor_artifact, CheckpointSelectionArtifact)
    assert anchor_artifact.result.selected_round.value == 118
