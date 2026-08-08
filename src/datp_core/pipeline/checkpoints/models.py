"""Authoritative persisted-checkpoint contracts for centralized and federated branches."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from datp_core.domain.enums import CheckpointSelectionRule, CheckpointStatus, ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RoundNumber, Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.protocols.training import AutoencoderArchitecture

RETAINED_CHECKPOINT_STATUSES = frozenset(
    {
        CheckpointStatus.CANDIDATE,
        CheckpointStatus.STABILITY_EVIDENCE,
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    }
)


@runtime_checkable
class PersistedCheckpoint(Protocol):
    """Minimum persisted-checkpoint shape shared by centralized and federated branches."""

    @property
    def round_number(self) -> RoundNumber: ...

    @property
    def tensor_path(self) -> Path: ...

    @property
    def tensor_checksum(self) -> Checksum: ...

    @property
    def mean_training_loss(self) -> MetricValue: ...

    @property
    def status(self) -> CheckpointStatus: ...


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
