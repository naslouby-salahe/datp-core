"""Federated checkpoint validation and fixed-terminal non-test selection."""

from collections.abc import Sequence
from dataclasses import replace

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    ProcessedDataBranch,
)
from datp_core.core.numeric import MetricValue
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.checkpoints.contracts import (
    CheckpointProtocol,
    realized_candidate_rounds,
    select_terminal_checkpoint,
    validate_ordered_checkpoint_inventory,
    validate_persisted_checkpoint_file,
)
from datp_core.detector.checkpoints.protocols import require_non_test_checkpoint_selection_inputs
from datp_core.detector.training.models import (
    CheckpointCandidate,
    CheckpointDecision,
    FederatedTrainingCoordinate,
)


def validate_candidate_coordinates(
    candidates: Sequence[CheckpointCandidate],
    coordinate: FederatedTrainingCoordinate,
    *,
    client: ClientIdentity | None,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
) -> None:
    for candidate in candidates:
        if candidate.coordinate != coordinate:
            raise ScientificContractError(
                ErrorMessage("checkpoint candidate coordinate mismatch"),
                subject=ContractSubject.COORDINATE,
            )
        if candidate.client != client:
            raise ScientificContractError(
                ErrorMessage("checkpoint candidate client mismatch"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if candidate.preprocessing_state_set_checksum != preprocessing_state_set_checksum:
            raise ScientificContractError(
                ErrorMessage("checkpoint candidate preprocessing checksum mismatch"),
                subject=ContractSubject.PREPROCESSING,
            )
        if candidate.split_manifest_checksum != split_manifest_checksum:
            raise ScientificContractError(
                ErrorMessage("checkpoint candidate split checksum mismatch"),
                subject=ContractSubject.SPLIT,
            )

        validate_persisted_checkpoint_file(
            candidate.tensor_path,
            candidate.tensor_checksum,
        )


def select_checkpoint(
    candidates: Sequence[CheckpointCandidate],
    protocol: CheckpointProtocol,
    *,
    coordinate: FederatedTrainingCoordinate,
    client: ClientIdentity | None,
    selection_rule: CheckpointSelectionRule,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
    held_out_metrics: Sequence[MetricValue] | None = None,
    attack_labels_present: bool = False,
) -> CheckpointDecision:
    require_non_test_checkpoint_selection_inputs(
        selection_rule=selection_rule,
        held_out_metrics=held_out_metrics,
        attack_labels_present=attack_labels_present,
        branch=ProcessedDataBranch.FEDERATED,
    )
    if not candidates:
        raise ScientificContractError(
            ErrorMessage("checkpoint selection requires candidates"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    realized = realized_candidate_rounds(protocol, candidates[-1].round_number)
    ordered = validate_ordered_checkpoint_inventory(
        candidates,
        realized,
    )
    validate_candidate_coordinates(
        ordered,
        coordinate,
        client=client,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    match selection_rule:
        case CheckpointSelectionRule.FINAL_COMPLETED_ROUND:
            terminal_round = realized[-1]
        case CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
            terminal_round = protocol.maximum_round
        case _:
            raise ScientificContractError(
                ErrorMessage("unsupported checkpoint selection rule"),
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
    selection = select_terminal_checkpoint(
        ordered,
        terminal_round=terminal_round,
        rebuild=lambda candidate, status: replace(candidate, status=status),
    )
    return CheckpointDecision(
        coordinate=coordinate,
        client=client,
        selected=selection.selected,
        candidates=selection.candidates,
        checkpoint_protocol=protocol,
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )
