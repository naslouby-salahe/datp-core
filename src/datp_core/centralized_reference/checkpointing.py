"""Centralized checkpoint candidate retention and non-test selection boundary."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.artifacts.serialization import canonical_checksum
from datp_core.centralized_reference.training import (
    CentralizedTrainingCoordinate,
    CentralizedTrainingExecution,
    InMemoryCentralizedModelSnapshot,
    assert_safetensors_reload,
    model_from_in_memory_snapshot,
    persist_state_dict_tensors,
)
from datp_core.domain.enums import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    TrainingModelId,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    Checksum,
    MetricValue,
    RoundNumber,
    Seed,
)
from datp_core.pipeline.checkpoints.models import RETAINED_CHECKPOINT_STATUSES
from datp_core.pipeline.checkpoints.persistence import (
    validate_persisted_checkpoint_file,
)
from datp_core.pipeline.checkpoints.service import (
    select_terminal_checkpoint,
    validate_ordered_checkpoint_inventory,
)
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol
from datp_core.protocols.training import require_non_test_checkpoint_selection_inputs
from datp_core.runtime.compute import resolve_cuda_device


class CentralizedCheckpointAssetName(StrEnum):
    CANDIDATE_PREFIX = "checkpoint_round_"
    CANDIDATE_SUFFIX = ".safetensors"
    CANDIDATES_MANIFEST = "checkpoint_candidates.json"
    DECISION = "checkpoint_decision.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class CentralizedCheckpointCandidate:
    coordinate: CentralizedTrainingCoordinate
    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    training_seed: Seed
    autoencoder_widths: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.status not in RETAINED_CHECKPOINT_STATUSES:
            raise ScientificContractError(
                "centralized checkpoint candidate has an invalid status",
                subject=self.status,
            )


@dataclass(frozen=True, slots=True)
class CentralizedCheckpointDecision:
    coordinate: CentralizedTrainingCoordinate
    selected: CentralizedCheckpointCandidate
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    selection_rule: CheckpointSelectionRule
    status: CheckpointStatus

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError("checkpoint decision requires retained candidates")
        if self.selected not in self.candidates:
            raise ScientificContractError(
                "selected checkpoint must be one of the retained candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "centralized checkpoint decision status must be SELECTED_BY_NON_TEST_RULE",
                subject=self.status,
            )
        if self.selection_rule is not CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
            raise ScientificContractError(
                "centralized checkpoint decision must use FIXED_TERMINAL_MAXIMUM_ROUND",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "selected checkpoint must equal the declared maximum round",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "selected candidate status must be SELECTED_BY_NON_TEST_RULE",
                subject=self.selected.status,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedCheckpointSetEntry:
    round_number: RoundNumber
    tensor_checksum: Checksum
    status: CheckpointStatus


def candidate_tensor_name(round_number: RoundNumber) -> str:
    return (
        f"{CentralizedCheckpointAssetName.CANDIDATE_PREFIX}"
        f"{round_number.value}"
        f"{CentralizedCheckpointAssetName.CANDIDATE_SUFFIX}"
    )


def retain_centralized_checkpoint_candidates(
    execution: CentralizedTrainingExecution,
    autoencoder: AutoencoderProtocol,
) -> tuple[CentralizedCheckpointCandidate, ...]:
    """Persist every declared in-memory snapshot and return persisted candidate records."""
    training_result = execution.result
    protocol = training_result.checkpoint_protocol
    snapshots = execution.candidate_snapshots
    declared = tuple(candidate.value for candidate in protocol.candidates)
    observed = tuple(snapshot.round_number.value for snapshot in snapshots)
    if observed != declared:
        raise ScientificContractError(
            "checkpoint snapshots must match the declared candidate rounds exactly and in order",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    candidates: list[CentralizedCheckpointCandidate] = []
    for snapshot in snapshots:
        path = training_result.model_directory / candidate_tensor_name(snapshot.round_number)
        checksum = persist_state_dict_tensors(snapshot.state_dict, path)
        _verify_candidate_reload(snapshot, path, autoencoder)
        candidates.append(
            CentralizedCheckpointCandidate(
                coordinate=training_result.coordinate,
                round_number=snapshot.round_number,
                tensor_path=path,
                tensor_checksum=checksum,
                mean_training_loss=snapshot.mean_training_loss,
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_checksum=(training_result.preprocessing_state_checksum),
                split_manifest_checksum=training_result.split_manifest_checksum,
                training_seed=training_result.training_seed,
                autoencoder_widths=tuple(autoencoder.widths),
            )
        )
    return validate_ordered_checkpoint_inventory(
        tuple(candidates),
        protocol.candidates,
    )


def select_centralized_checkpoint(
    candidates: Sequence[CentralizedCheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
) -> CentralizedCheckpointDecision:
    """Select the maximum-round candidate without held-out or attack evidence."""
    require_non_test_checkpoint_selection_inputs(
        selection_rule=selection_rule,
        held_out_metrics=held_out_metrics,
        attack_labels_present=attack_labels_present,
        branch_label="centralized",
    )
    ordered = validate_ordered_checkpoint_inventory(
        candidates,
        protocol.candidates,
    )
    for candidate in ordered:
        if candidate.status is CheckpointStatus.HISTORICAL_ENDPOINT:
            raise ScientificContractError(
                "historical federated endpoint status is incompatible with centralized candidates",
                subject=candidate.status,
            )
        validate_persisted_checkpoint_file(
            candidate.tensor_path,
            candidate.tensor_checksum,
        )

    statused, selected = select_terminal_checkpoint(
        ordered,
        protocol.maximum_round,
        rebuild=_rebuild_candidate_status,
    )
    return CentralizedCheckpointDecision(
        coordinate=selected.coordinate,
        selected=selected,
        candidates=statused,
        checkpoint_protocol=protocol,
        selection_rule=selection_rule,
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )


def _rebuild_candidate_status(
    candidate: CentralizedCheckpointCandidate,
    status: CheckpointStatus,
) -> CentralizedCheckpointCandidate:
    return CentralizedCheckpointCandidate(
        coordinate=candidate.coordinate,
        round_number=candidate.round_number,
        tensor_path=candidate.tensor_path,
        tensor_checksum=candidate.tensor_checksum,
        mean_training_loss=candidate.mean_training_loss,
        status=status,
        preprocessing_state_checksum=candidate.preprocessing_state_checksum,
        split_manifest_checksum=candidate.split_manifest_checksum,
        training_seed=candidate.training_seed,
        autoencoder_widths=candidate.autoencoder_widths,
    )


def reject_federated_checkpoint(identity: TrainingModelId) -> None:
    raise LeakageError(
        f"federated checkpoint cannot enter centralized scoring or selection ({identity.value})",
        subject=ContractSubject.CHECKPOINT_CANDIDATES,
    )


def validate_candidate_coordinates(
    candidates: Sequence[CentralizedCheckpointCandidate],
    coordinate: CentralizedTrainingCoordinate,
    *,
    preprocessing_checksum: Checksum,
    split_checksum: Checksum,
    training_seed: Seed,
) -> None:
    for candidate in candidates:
        if candidate.coordinate != coordinate:
            raise ScientificContractError(
                "checkpoint candidate coordinate mismatch",
                subject=ContractSubject.COORDINATE,
            )
        if candidate.preprocessing_state_checksum != preprocessing_checksum:
            raise ScientificContractError(
                "checkpoint candidate preprocessing checksum mismatch",
                subject=ContractSubject.PREPROCESSING,
            )
        if candidate.split_manifest_checksum != split_checksum:
            raise ScientificContractError(
                "checkpoint candidate split checksum mismatch",
                subject=ContractSubject.SPLIT,
            )
        if candidate.training_seed != training_seed:
            raise ScientificContractError(
                "checkpoint candidate training seed mismatch",
                subject=ContractSubject.SEED,
            )


def candidate_set_checksum(
    candidates: Sequence[CentralizedCheckpointCandidate],
) -> Checksum:
    return canonical_checksum(
        tuple(
            CentralizedCheckpointSetEntry(
                round_number=item.round_number,
                tensor_checksum=item.tensor_checksum,
                status=item.status,
            )
            for item in candidates
        )
    )


def _verify_candidate_reload(
    snapshot: InMemoryCentralizedModelSnapshot,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> None:
    device = resolve_cuda_device()
    model = model_from_in_memory_snapshot(snapshot, autoencoder, device)
    assert_safetensors_reload(model, path, device)
