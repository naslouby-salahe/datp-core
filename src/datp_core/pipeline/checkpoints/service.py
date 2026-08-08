"""Centralized and federated checkpoint retention, validation, and selection."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.detector.checkpoints.contracts import CheckpointProtocol, validate_persisted_checkpoint_file
from datp_core.detector.checkpoints.contracts import (
    select_terminal_checkpoint as apply_terminal_selection,
)
from datp_core.detector.checkpoints.contracts import (
    validate_ordered_checkpoint_inventory as validate_inventory,
)
from datp_core.detector.training.centralized import (
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
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RoundNumber, Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.learning.federated.checkpoints.selection import select_checkpoint
from datp_core.learning.federated.checkpoints.selection import (
    validate_candidate_coordinates as validate_federated_candidates,
)
from datp_core.detector.training.models import (
    CheckpointCandidate,
    CheckpointDecision,
    FederatedTrainingCoordinate,
)
from datp_core.pipeline.checkpoints.models import (
    CentralizedCheckpointAssetName,
    CentralizedCheckpointCandidate,
    CentralizedCheckpointDecision,
    CentralizedCheckpointSetEntry,
    PersistedCheckpoint,
)
from datp_core.protocols.training import (
    CHECKPOINT_SELECTION_RULE,
    AutoencoderProtocol,
    require_non_test_checkpoint_selection_inputs,
)
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectFederatedCheckpointRequest:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity | None
    candidates: tuple[CheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    held_out_metrics: tuple[MetricValue, ...] | None
    attack_labels_present: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectCentralizedCheckpointRequest:
    coordinate: CentralizedTrainingCoordinate
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_checksum: Checksum
    split_checksum: Checksum
    training_seed: Seed
    held_out_metrics: tuple[MetricValue, ...] | None
    attack_labels_present: bool


def validate_ordered_checkpoint_inventory[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    expected_rounds: tuple[RoundNumber, ...],
) -> tuple[CandidateT, ...]:
    return validate_inventory(candidates, expected_rounds)


def select_terminal_checkpoint[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    maximum_round: RoundNumber,
    *,
    rebuild: Callable[[CandidateT, CheckpointStatus], CandidateT],
) -> tuple[tuple[CandidateT, ...], CandidateT]:
    return apply_terminal_selection(candidates, maximum_round, rebuild=rebuild)


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
                preprocessing_state_checksum=training_result.preprocessing_state_checksum,
                split_manifest_checksum=training_result.split_manifest_checksum,
                training_seed=training_result.training_seed,
                autoencoder_widths=autoencoder.widths,
            )
        )
    return validate_ordered_checkpoint_inventory(tuple(candidates), protocol.candidates)


def select_centralized_checkpoint(
    candidates: Sequence[CentralizedCheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
) -> CentralizedCheckpointDecision:
    require_non_test_checkpoint_selection_inputs(
        selection_rule=selection_rule,
        held_out_metrics=held_out_metrics,
        attack_labels_present=attack_labels_present,
        branch_label="centralized",
    )
    ordered = validate_ordered_checkpoint_inventory(candidates, protocol.candidates)
    for candidate in ordered:
        if candidate.status is CheckpointStatus.HISTORICAL_ENDPOINT:
            raise ScientificContractError(
                "historical federated endpoint status is incompatible with centralized candidates",
                subject=candidate.status,
            )
        validate_persisted_checkpoint_file(candidate.tensor_path, candidate.tensor_checksum)
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


def reject_federated_checkpoint(identity: TrainingModelId) -> None:
    raise LeakageError(
        f"federated checkpoint cannot enter centralized scoring or selection ({identity.value})",
        subject=ContractSubject.CHECKPOINT_CANDIDATES,
    )


def validate_centralized_candidate_coordinates(
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


def centralized_candidate_set_checksum(
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


def select_federated_primary_checkpoint(request: SelectFederatedCheckpointRequest) -> CheckpointDecision:
    validate_federated_candidates(
        request.candidates,
        request.coordinate,
        client=request.client,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    return select_checkpoint(
        request.candidates,
        request.checkpoint_protocol,
        coordinate=request.coordinate,
        client=request.client,
        selection_rule=CHECKPOINT_SELECTION_RULE,
        held_out_metrics=request.held_out_metrics,
        attack_labels_present=request.attack_labels_present,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


def select_centralized_primary_checkpoint(
    request: SelectCentralizedCheckpointRequest,
) -> CentralizedCheckpointDecision:
    validate_centralized_candidate_coordinates(
        request.candidates,
        request.coordinate,
        preprocessing_checksum=request.preprocessing_checksum,
        split_checksum=request.split_checksum,
        training_seed=request.training_seed,
    )
    return select_centralized_checkpoint(
        request.candidates,
        request.checkpoint_protocol,
        selection_rule=CHECKPOINT_SELECTION_RULE,
        held_out_metrics=request.held_out_metrics,
        attack_labels_present=request.attack_labels_present,
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


def _verify_candidate_reload(
    snapshot: InMemoryCentralizedModelSnapshot,
    path: Path,
    autoencoder: AutoencoderProtocol,
) -> None:
    device = resolve_cuda_device()
    model = model_from_in_memory_snapshot(snapshot, autoencoder, device)
    assert_safetensors_reload(model, path, device)
