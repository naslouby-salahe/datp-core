"""Typed preprocessing protocols, partitions, fitted state, and transform results."""

from dataclasses import dataclass
from enum import StrEnum

import polars as pl
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    ContractSubject,
    FeatureNameSequence,
    OutcomeLabelSequence,
    PartitionRole,
    PreprocessingProtocolId,
    StableRowIdSequence,
)
from datp_core.core.numeric import RowCount
from datp_core.data.populations.contracts import ClientIdentity


type TrustedScaler = StandardScaler | MinMaxScaler


class PreprocessingFitScope(StrEnum):
    CLIENT_LOCAL_TRAINING = "client_local_training"
    POOLED_TRAINING = "pooled_training"


class ScalerFamily(StrEnum):
    STANDARD = "standard"
    MIN_MAX = "min_max"
    COLUMN_ORDER_PROJECTION = "column_order_projection"


@dataclass(frozen=True, slots=True)
class PreprocessingProtocol:
    identity: PreprocessingProtocolId
    feature_names: FeatureNameSequence
    fit_scope: PreprocessingFitScope
    scaler_family: ScalerFamily

    def __post_init__(self) -> None:
        match self.identity:
            case PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD:
                expected = (PreprocessingFitScope.CLIENT_LOCAL_TRAINING, ScalerFamily.STANDARD)
            case PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX:
                expected = (PreprocessingFitScope.POOLED_TRAINING, ScalerFamily.MIN_MAX)
            case PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX:
                expected = (PreprocessingFitScope.POOLED_TRAINING, ScalerFamily.MIN_MAX)
            case PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION:
                expected = (PreprocessingFitScope.POOLED_TRAINING, ScalerFamily.COLUMN_ORDER_PROJECTION)
        if (self.fit_scope, self.scaler_family) != expected:
            raise ScientificContractError(
                "preprocessing protocol identity disagrees with its locked fit scope or scaler family",
                subject=ContractSubject.PREPROCESSING,
            )


@dataclass(slots=True, eq=False)
class PreprocessingPartition:
    role: PartitionRole
    frame: pl.DataFrame
    row_ids: StableRowIdSequence
    outcome_labels: OutcomeLabelSequence

    def __post_init__(self) -> None:
        if self.frame.height != len(self.row_ids) or self.frame.height != len(self.outcome_labels):
            raise ScientificContractError(
                "preprocessing partition frame, row identities, and labels must have equal length",
                subject=ContractSubject.PREPROCESSING,
            )
        if len(frozenset(self.row_ids.row_ids)) != len(self.row_ids):
            raise ScientificContractError(
                "preprocessing partition row identities must be unique",
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class PreprocessingPartitions:
    partitions: tuple[PreprocessingPartition, ...]

    def __post_init__(self) -> None:
        if not self.partitions:
            raise ScientificContractError(
                "preprocessing requires at least one partition",
                subject=ContractSubject.PREPROCESSING,
            )
        roles = tuple(item.role for item in self.partitions)
        if len(frozenset(roles)) != len(roles):
            raise ScientificContractError(
                "preprocessing partitions must be unique by role",
                subject=ContractSubject.PREPROCESSING,
            )
        if PartitionRole.TRAIN not in roles:
            raise ScientificContractError(
                "preprocessing requires a training partition",
                subject=ContractSubject.PREPROCESSING,
            )

    def require(self, role: PartitionRole) -> PreprocessingPartition:
        matches = tuple(item for item in self.partitions if item.role is role)
        if len(matches) != 1:
            raise ScientificContractError(
                f"preprocessing requires exactly one {role.value} partition",
                subject=ContractSubject.PREPROCESSING,
            )
        return matches[0]

    def optional(self, role: PartitionRole) -> PreprocessingPartition | None:
        matches = tuple(item for item in self.partitions if item.role is role)
        if len(matches) > 1:
            raise ScientificContractError(
                f"preprocessing contains duplicate {role.value} partitions",
                subject=ContractSubject.PREPROCESSING,
            )
        return matches[0] if matches else None


@dataclass(frozen=True, slots=True)
class ClientPreprocessingInput:
    client: ClientIdentity
    partitions: PreprocessingPartitions


@dataclass(frozen=True, slots=True, eq=False)
class FittedPreprocessingState:
    protocol: PreprocessingProtocol
    estimator: TrustedScaler
    fit_row_count: RowCount
    fit_row_checksum: Checksum
    owner: ClientIdentity | None

    def __post_init__(self) -> None:
        if self.fit_row_count.value < 1:
            raise ScientificContractError(
                "preprocessing fit state requires at least one training row",
                subject=ContractSubject.PREPROCESSING,
            )
        if self.protocol.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING and self.owner is None:
            raise ScientificContractError(
                "client-local preprocessing state requires a client owner",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if self.protocol.fit_scope is PreprocessingFitScope.POOLED_TRAINING and self.owner is not None:
            raise ScientificContractError(
                "pooled preprocessing state must not claim one client owner",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True, eq=False)
class ClientFittedPreprocessing:
    client: ClientIdentity
    state: FittedPreprocessingState

    def __post_init__(self) -> None:
        if self.state.owner is not None and self.state.owner != self.client:
            raise ScientificContractError(
                "client preprocessing state owner must match the client",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True, eq=False)
class FederatedFittedPreprocessing:
    protocol: PreprocessingProtocol
    clients: tuple[ClientFittedPreprocessing, ...]
    pooled_state: FittedPreprocessingState | None

    def __post_init__(self) -> None:
        if not self.clients:
            raise ScientificContractError(
                "federated preprocessing requires at least one client",
                subject=ContractSubject.PREPROCESSING,
            )
        identities = tuple(item.client for item in self.clients)
        if len(frozenset(identities)) != len(identities):
            raise ScientificContractError(
                "federated preprocessing clients must be unique",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if self.protocol.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            if self.pooled_state is not None or any(item.state.owner != item.client for item in self.clients):
                raise ScientificContractError(
                    "client-local preprocessing requires one distinct client-owned state per client",
                    subject=ContractSubject.PREPROCESSING,
                )
        else:
            if self.pooled_state is None or any(item.state is not self.pooled_state for item in self.clients):
                raise ScientificContractError(
                    "pooled preprocessing requires one shared fitted state",
                    subject=ContractSubject.PREPROCESSING,
                )


@dataclass(slots=True, eq=False)
class TransformedPartition:
    role: PartitionRole
    frame: pl.DataFrame
    row_ids: StableRowIdSequence
    outcome_labels: OutcomeLabelSequence

    def __post_init__(self) -> None:
        if self.frame.height != len(self.row_ids) or self.frame.height != len(self.outcome_labels):
            raise ScientificContractError(
                "transformed partition must preserve row and label cardinality",
                subject=ContractSubject.PREPROCESSING,
            )


@dataclass(frozen=True, slots=True, eq=False)
class ClientPreprocessingResult:
    client: ClientIdentity
    state: FittedPreprocessingState
    partitions: tuple[TransformedPartition, ...]

    def require(self, role: PartitionRole) -> TransformedPartition:
        matches = tuple(item for item in self.partitions if item.role is role)
        if len(matches) != 1:
            raise ScientificContractError(
                f"client preprocessing result requires exactly one {role.value} partition",
                subject=ContractSubject.PREPROCESSING,
            )
        return matches[0]


@dataclass(frozen=True, slots=True, eq=False)
class FederatedPreprocessingResult:
    fitted: FederatedFittedPreprocessing
    clients: tuple[ClientPreprocessingResult, ...]

    def __post_init__(self) -> None:
        fitted_clients = tuple(item.client for item in self.fitted.clients)
        result_clients = tuple(item.client for item in self.clients)
        if fitted_clients != result_clients:
            raise ScientificContractError(
                "fitted and transformed client order must match exactly",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedPreprocessingInput:
    protocol: PreprocessingProtocol
    partitions: PreprocessingPartitions


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedPreprocessingResult:
    state: FittedPreprocessingState
    partitions: tuple[TransformedPartition, ...]

    def require(self, role: PartitionRole) -> TransformedPartition:
        matches = tuple(item for item in self.partitions if item.role is role)
        if len(matches) != 1:
            raise ScientificContractError(
                f"centralized preprocessing result requires exactly one {role.value} partition",
                subject=ContractSubject.PREPROCESSING,
            )
        return matches[0]
