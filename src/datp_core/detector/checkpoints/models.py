"""Authoritative persisted-checkpoint contracts for centralized and federated branches."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import CheckpointSelectionRule, CheckpointStatus, ContractSubject
from datp_core.core.numeric import MetricValue, RoundNumber, Seed
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.checkpoints.protocols import RETAINED_CHECKPOINT_STATUSES
from datp_core.detector.training.centralized import CentralizedTrainingCoordinate
from datp_core.detector.training.contracts import AutoencoderArchitecture


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
    autoencoder_widths: AutoencoderArchitecture

    def __post_init__(self) -> None:
        if self.status not in RETAINED_CHECKPOINT_STATUSES:
            raise ScientificContractError(
                ErrorMessage("centralized checkpoint candidate has an invalid status"),
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
                ErrorMessage("selected checkpoint must be one of the retained candidates"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                ErrorMessage("centralized checkpoint decision status must be SELECTED_BY_NON_TEST_RULE"),
                subject=self.status,
            )
        if self.selection_rule is not CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
            raise ScientificContractError(
                ErrorMessage("centralized checkpoint decision must use FIXED_TERMINAL_MAXIMUM_ROUND"),
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                ErrorMessage("selected checkpoint must equal the declared maximum round"),
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                ErrorMessage("selected candidate status must be SELECTED_BY_NON_TEST_RULE"),
                subject=self.selected.status,
            )
