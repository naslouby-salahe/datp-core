"""Immutable population, partition, split, and feasibility records."""

from dataclasses import dataclass
from enum import StrEnum
from functools import total_ordering
from math import floor, fsum
from pathlib import Path

import polars as pl
from pydantic import model_validator

from datp_core.datasets.models import CanonicalProvenanceColumn
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CapabilityStatus,
    ControlledPartitionKind,
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.domain.values import (
    Checksum,
    ClientCount,
    DirichletConcentration,
    RowCount,
    Seed,
    checksum_text,
    floats_absolutely_close,
)
from datp_core.protocols.models import FRACTION_TOTAL_ABSOLUTE_TOLERANCE, UNIT_FRACTION_TOTAL
from datp_core.protocols.runtime import DATA_ROOT


class PopulationOutcomeLabel(StrEnum):
    BENIGN = "benign"
    ATTACK = "attack"


class PopulationFrameColumn(StrEnum):
    """Canonical column names for population membership and split assignment frames."""

    CLIENT_ID = "client_id"
    OUTCOME_LABEL = "outcome_label"
    PARTITION_ROLE = "partition_role"
    FAMILY_ID = "family_id"
    STABLE_ROW_ID = CanonicalProvenanceColumn.STABLE_ROW_ID.value
    SOURCE_PATH = CanonicalProvenanceColumn.SOURCE_PATH.value
    SOURCE_ROW_INDEX = CanonicalProvenanceColumn.SOURCE_ROW_INDEX.value


class PopulationManifestField(StrEnum):
    """Manifest field identities used as validation subjects."""

    CANDIDATE_CLIENTS = "candidate_clients"
    ACCEPTED_CLIENTS = "accepted_clients"
    EXCLUDED_CLIENT_IDS = "excluded_client_ids"
    TOTAL_MEMBERSHIP_ROWS = "total_membership_rows"
    BENIGN_ROW_COUNT = "benign_row_count"
    ATTACK_ROW_COUNT = "attack_row_count"


class WorkingFrameColumn(StrEnum):
    """Ephemeral Polars helper columns used only inside population algorithms."""

    ORDER = "_order"
    PERM = "_perm"
    MAX_HISTORICAL = "max_historical_timestamp"
    MIN_FUTURE = "min_future_timestamp"


class CohortAggregationColumn(StrEnum):
    """Aggregation aliases for threshold-independent cohort support counts."""

    BENIGN_CALIBRATION_COUNT = "benign_calibration_count"
    BENIGN_EVALUATION_COUNT = "benign_evaluation_count"
    ATTACK_EVALUATION_COUNT = "attack_evaluation_count"


CLIENT_ID_COLUMN = PopulationFrameColumn.CLIENT_ID
STABLE_ROW_ID_COLUMN = PopulationFrameColumn.STABLE_ROW_ID
OUTCOME_LABEL_COLUMN = PopulationFrameColumn.OUTCOME_LABEL
PARTITION_ROLE_COLUMN = PopulationFrameColumn.PARTITION_ROLE
SOURCE_PATH_COLUMN = PopulationFrameColumn.SOURCE_PATH
SOURCE_ROW_INDEX_COLUMN = PopulationFrameColumn.SOURCE_ROW_INDEX
FAMILY_ID_COLUMN = PopulationFrameColumn.FAMILY_ID
ORDER_COLUMN = WorkingFrameColumn.ORDER
PERM_COLUMN = WorkingFrameColumn.PERM

MEMBERSHIP_COLUMNS: tuple[PopulationFrameColumn, ...] = (
    PopulationFrameColumn.CLIENT_ID,
    PopulationFrameColumn.STABLE_ROW_ID,
    PopulationFrameColumn.OUTCOME_LABEL,
    PopulationFrameColumn.SOURCE_PATH,
    PopulationFrameColumn.SOURCE_ROW_INDEX,
)
ASSIGNMENT_COLUMNS: tuple[PopulationFrameColumn, ...] = MEMBERSHIP_COLUMNS + (PopulationFrameColumn.PARTITION_ROLE,)
PARQUET_GLOB = "*.parquet"


def membership_column_names() -> tuple[str, ...]:
    return tuple(column.value for column in MEMBERSHIP_COLUMNS)


def assignment_column_names() -> tuple[str, ...]:
    return tuple(column.value for column in ASSIGNMENT_COLUMNS)


def select_membership_frame(frame: pl.DataFrame) -> pl.DataFrame:
    """Select the locked membership schema from a Polars DataFrame."""
    return frame.select(membership_column_names())


def canonical_data_glob(canonical_root: Path) -> str:
    return str(Path(canonical_root) / DATA_ROOT / PARQUET_GLOB)


def canonical_branch_directory(canonical_root: Path, branch: StrEnum) -> Path:
    return Path(canonical_root) / DATA_ROOT / branch.value


class PopulationFeasibilityStatus(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"


class PopulationFeasibilityReason(StrEnum):
    CANDIDATE_SET_MATCHES_DECLARATION = "candidate_set_matches_declaration"
    CANDIDATE_COUNT_MISMATCH = "candidate_count_mismatch"
    IDENTITY_SET_MISMATCH = "identity_set_mismatch"
    CHRONOLOGY_EVIDENCE_INSUFFICIENT = "chronology_evidence_insufficient"
    DATASET_CAPABILITY_PROHIBITS = "dataset_capability_prohibits"
    EMPTY_ACCEPTED_CLIENTS = "empty_accepted_clients"


class ChronologyExclusionReason(StrEnum):
    """Auditable reasons a static sensor group is inadmissible for temporal execution."""

    CANONICAL_CHRONOLOGY_MISSING = "canonical_chronology_missing"
    CANONICAL_CHRONOLOGY_INELIGIBLE = "canonical_chronology_ineligible"
    MODBUS_ADDRESS_LITERAL = "modbus_address_literal"


class PopulationManifestDocument(StrictModel):
    population: PopulationId
    dataset: DatasetId
    identity_kind: PopulationIdentityKind
    partition_seed: Seed
    split_protocol: SplitProtocolId
    candidate_clients: tuple[str, ...]
    accepted_clients: tuple[str, ...]
    excluded_client_ids: tuple[str, ...]
    total_membership_rows: RowCount
    benign_row_count: RowCount
    attack_row_count: RowCount
    membership_checksum: Checksum
    canonical_schema_checksum: Checksum
    feasibility_status: PopulationFeasibilityStatus
    feasibility_reason: PopulationFeasibilityReason

    @model_validator(mode="after")
    def validate_manifest(self) -> "PopulationManifestDocument":
        _require_unique_ordered(self.candidate_clients, PopulationManifestField.CANDIDATE_CLIENTS)
        _require_unique_ordered(self.accepted_clients, PopulationManifestField.ACCEPTED_CLIENTS)
        _require_unique_ordered(self.excluded_client_ids, PopulationManifestField.EXCLUDED_CLIENT_IDS)
        _require_client_set_partition(self.candidate_clients, self.accepted_clients, self.excluded_client_ids)
        _require_non_negative_row_counts(self.total_membership_rows, self.benign_row_count, self.attack_row_count)
        return self


class SplitManifestDocument(StrictModel):
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    assignment_row_count: RowCount
    train_row_count: RowCount
    calibration_row_count: RowCount
    evaluation_row_count: RowCount
    future_recalibration_row_count: RowCount
    static_reference_reserve_row_count: RowCount
    assignment_checksum: Checksum
    population_manifest_checksum: Checksum

    @model_validator(mode="after")
    def validate_manifest(self) -> "SplitManifestDocument":
        counts = (
            self.train_row_count,
            self.calibration_row_count,
            self.evaluation_row_count,
            self.future_recalibration_row_count,
            self.static_reference_reserve_row_count,
        )
        if sum(counts) != self.assignment_row_count:
            raise ValueError("partition role counts must sum to assignment rows")
        return self


class DirichletPartitionDiagnosticsDocument(StrictModel):
    population: PopulationId
    partition_seed: Seed
    partition_kind: ControlledPartitionKind
    concentration: DirichletConcentration | None
    client_count: ClientCount
    client_ids: tuple[str, ...]
    total_rows: RowCount
    client_row_counts: tuple[RowCount, ...]
    benign_row_counts: tuple[RowCount, ...]
    attack_row_counts: tuple[RowCount, ...]
    empty_client_ids: tuple[str, ...]
    insufficient_benign_client_ids: tuple[str, ...]
    allocation_checksum: Checksum

    @model_validator(mode="after")
    def validate_diagnostics(self) -> "DirichletPartitionDiagnosticsDocument":
        _require_client_series_shape(self)
        _require_row_conservation(self)
        _require_partition_kind_fields(self)
        return self


class ChronologicalPartitionDiagnosticsDocument(StrictModel):
    population: PopulationId
    expected_group_count: ClientCount
    observed_eligible_group_count: ClientCount
    eligible_group_ids: tuple[str, ...]
    excluded_group_ids: tuple[str, ...]
    exclusion_reasons: tuple[ChronologyExclusionReason, ...]
    duplicate_timestamp_rows: RowCount
    total_temporal_rows: RowCount

    @model_validator(mode="after")
    def validate_diagnostics(self) -> "ChronologicalPartitionDiagnosticsDocument":
        if self.observed_eligible_group_count.value != len(self.eligible_group_ids):
            raise ValueError("observed eligible count must match eligible identities")
        if len(self.excluded_group_ids) != len(self.exclusion_reasons):
            raise ValueError("each excluded group requires one typed reason")
        if min(
            self.duplicate_timestamp_rows.value,
            self.total_temporal_rows.value,
            self.observed_eligible_group_count.value,
        ) < 0:
            raise ValueError("chronology diagnostic counts must be non-negative")
        return self


@dataclass(frozen=True, slots=True)
class ClientPartitionCounts:
    """Per-client partition support counts used to construct evaluation cohorts."""

    client_id: str
    benign_calibration_count: RowCount
    benign_evaluation_count: RowCount
    attack_evaluation_count: RowCount
    accepted: bool
    deployment_fallback: bool

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError("client partition counts require a client identity")


@total_ordering
@dataclass(frozen=True, slots=True)
class ClientIdentity:
    population: PopulationId
    client_id: str
    identity_kind: PopulationIdentityKind

    def __post_init__(self) -> None:
        if not self.client_id or any(separator in self.client_id for separator in ("=", "/", "\\")):
            raise ValueError("client identity must be a non-empty path-safe token")

    def __lt__(self, other: "ClientIdentity") -> bool:
        return self.client_id < other.client_id


@dataclass(frozen=True, slots=True)
class PopulationCapabilities:
    population: PopulationId
    dataset: DatasetId
    identity_kind: PopulationIdentityKind
    declared_client_count: ClientCount
    physical_client_validity: CapabilityStatus
    family_taxonomy: CapabilityStatus
    chronology: CapabilityStatus
    client_level_attack_assignment: CapabilityStatus
    fpr_evaluation: CapabilityStatus
    attack_sensitive_evaluation: CapabilityStatus
    temporal_support: CapabilityStatus
    valid_threshold_methods: tuple[FederatedThresholdMethod, ...]
    evidentiary_role: EvidenceRole
    confirmatory_eligible: bool

    def __post_init__(self) -> None:
        if len(self.valid_threshold_methods) != len(frozenset(self.valid_threshold_methods)):
            raise ValueError("valid threshold methods must be unique")


@dataclass(frozen=True, slots=True)
class PopulationFeasibility:
    status: PopulationFeasibilityStatus
    reason: PopulationFeasibilityReason
    expected_client_count: ClientCount
    observed_client_count: ClientCount
    evidence: str

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("feasibility requires evidence")


@dataclass(frozen=True, slots=True)
class PopulationManifest:
    document: PopulationManifestDocument
    clients: tuple[ClientIdentity, ...]
    feasibility: PopulationFeasibility
    family_by_client: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        client_ids = tuple(client.client_id for client in self.clients)
        if client_ids != self.document.candidate_clients:
            raise ValueError("manifest clients must match candidate client identities in order")


@dataclass(frozen=True, slots=True)
class ControlledPartitionCondition:
    kind: ControlledPartitionKind
    concentration: DirichletConcentration | None

    def __post_init__(self) -> None:
        match self.kind:
            case ControlledPartitionKind.DIRICHLET:
                if self.concentration is None:
                    raise ValueError("Dirichlet construction requires a positive concentration")
            case ControlledPartitionKind.IID:
                if self.concentration is not None:
                    raise ValueError("IID construction must not carry a concentration")


@dataclass(frozen=True, slots=True, eq=False)
class SplitConstructionRequest:
    """Typed request boundary for residual and chronological splits."""

    membership: pl.DataFrame
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    population_manifest_checksum: Checksum
    capture_timestamp_column: str | None = None


def dirichlet_condition(concentration: DirichletConcentration) -> ControlledPartitionCondition:
    return ControlledPartitionCondition(ControlledPartitionKind.DIRICHLET, concentration)


def iid_condition() -> ControlledPartitionCondition:
    return ControlledPartitionCondition(ControlledPartitionKind.IID, None)


def client_identities(
    population: PopulationId,
    client_ids: tuple[str, ...],
    identity_kind: PopulationIdentityKind,
) -> tuple[ClientIdentity, ...]:
    return tuple(ClientIdentity(population, client_id, identity_kind) for client_id in client_ids)


def build_population_manifest(
    document: PopulationManifestDocument,
    feasibility: PopulationFeasibility,
    family_by_client: tuple[tuple[str, str], ...] = (),
) -> PopulationManifest:
    return PopulationManifest(
        document,
        client_identities(document.population, document.candidate_clients, document.identity_kind),
        feasibility,
        family_by_client,
    )


def hamilton_integer_counts(total: int, ratios: tuple[float, ...]) -> tuple[int, ...]:
    """Largest-remainder (Hamilton) integer allocation.

    For non-negative integer ``total`` and ratios that sum to one:

    1. compute raw shares ``total * ratio_i``;
    2. assign each role ``floor(raw_i)``;
    3. distribute the residual ``total - sum(floors)`` by descending fractional part;
    4. break fractional ties by ascending role index.

    The result conserves every row exactly once and never depends on library defaults.
    """
    _require_hamilton_inputs(total, ratios)
    raw = tuple(total * ratio for ratio in ratios)
    floors = tuple(floor(value) for value in raw)
    residual = total - sum(floors)
    order = sorted(range(len(ratios)), key=lambda index: (-(raw[index] - floors[index]), index))
    extras = [0] * len(ratios)
    for index in order[:residual]:
        extras[index] = 1
    return tuple(floor_value + extra for floor_value, extra in zip(floors, extras, strict=True))


def synthetic_client_ids(client_count: ClientCount) -> tuple[str, ...]:
    width = max(2, len(str(client_count.value - 1)))
    return tuple(f"synthetic_client_{index:0{width}d}" for index in range(client_count.value))


def membership_checksum(client_ids: tuple[str, ...], stable_row_ids: tuple[str, ...]) -> Checksum:
    payload = "\n".join((*client_ids, *stable_row_ids))
    return checksum_text(payload)


def _require_hamilton_inputs(total: int, ratios: tuple[float, ...]) -> None:
    if total < 0:
        raise ValueError("Hamilton allocation requires a non-negative total")
    if not ratios or any(ratio < 0 for ratio in ratios):
        raise ValueError("Hamilton allocation requires non-negative ratios that sum to one")
    if not floats_absolutely_close(fsum(ratios), UNIT_FRACTION_TOTAL, FRACTION_TOTAL_ABSOLUTE_TOLERANCE):
        raise ValueError("Hamilton allocation requires non-negative ratios that sum to one")


def _require_unique_ordered(values: tuple[str, ...], field: PopulationManifestField) -> None:
    if len(values) != len(frozenset(values)):
        raise ValueError(f"{field.value} must be unique")


def _require_client_set_partition(
    candidates: tuple[str, ...],
    accepted: tuple[str, ...],
    excluded: tuple[str, ...],
) -> None:
    accepted_set = frozenset(accepted)
    if not accepted_set <= frozenset(candidates):
        raise ValueError(f"{PopulationManifestField.ACCEPTED_CLIENTS.value} must be a subset of candidates")
    if frozenset(excluded) & accepted_set:
        raise ValueError(f"{PopulationManifestField.EXCLUDED_CLIENT_IDS.value} cannot also be accepted")


def _require_non_negative_row_counts(total: RowCount, benign: RowCount, attack: RowCount) -> None:
    if benign + attack != total:
        raise ValueError("benign and attack rows must sum to total membership rows")


def _require_client_series_shape(document: DirichletPartitionDiagnosticsDocument) -> None:
    expected = document.client_count.value
    if len(document.client_ids) != expected:
        raise ValueError("client identity count must match declared client count")
    for series in (document.client_row_counts, document.benign_row_counts, document.attack_row_counts):
        if len(series) != expected:
            raise ValueError("per-client count series must be complete")


def _require_row_conservation(document: DirichletPartitionDiagnosticsDocument) -> None:
    if sum(document.client_row_counts) != document.total_rows:
        raise ValueError("client row counts must conserve total rows")
    if sum(document.benign_row_counts) + sum(document.attack_row_counts) != document.total_rows:
        raise ValueError("benign and attack counts must conserve total rows")


def _require_partition_kind_fields(document: DirichletPartitionDiagnosticsDocument) -> None:
    match document.partition_kind:
        case ControlledPartitionKind.DIRICHLET:
            if document.concentration is None or document.concentration <= 0:
                raise ValueError("Dirichlet diagnostics require a positive concentration")
        case ControlledPartitionKind.IID:
            if document.concentration is not None:
                raise ValueError("IID diagnostics must not carry a Dirichlet concentration")
