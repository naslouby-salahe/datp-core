"""Immutable population, partition, split, feasibility, and construction contracts."""

from dataclasses import dataclass
from enum import StrEnum
from functools import reduce, total_ordering
from pathlib import Path

import polars as pl
from pydantic import model_validator

from datp_core.datasets.capabilities import CapabilityStatus, DatasetCapabilities
from datp_core.datasets.contracts import CanonicalProvenanceColumn
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.domain.errors import CapabilityError
from datp_core.domain.values.base import NonNegativeIntegerValue
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.domain.values.counts import ClientCount, RowCount, Seed
from datp_core.domain.values.identifiers import CaptureTimestampColumn
from datp_core.domain.values.ratios import DirichletConcentration
from datp_core.protocols.populations import PopulationDeclaration


class ControlledPartitionKind(StrEnum):
    """Construction kind for controlled synthetic client partitions.

    IID is a separate typed construction condition, never an infinite Dirichlet concentration.
    """

    DIRICHLET = "dirichlet"
    IID = "iid"


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
    """Ephemeral Polars helper columns used only inside partitioning algorithms."""

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


def membership_column_names() -> tuple[str, ...]:
    return tuple(column.value for column in MEMBERSHIP_COLUMNS)


def assignment_column_names() -> tuple[str, ...]:
    return tuple(column.value for column in ASSIGNMENT_COLUMNS)


def select_membership_frame(frame: pl.DataFrame) -> pl.DataFrame:
    """Select the locked membership schema from a Polars DataFrame."""
    return frame.select(membership_column_names())


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
        _require_unique_ordered(
            self.candidate_clients,
            PopulationManifestField.CANDIDATE_CLIENTS,
        )
        _require_unique_ordered(
            self.accepted_clients,
            PopulationManifestField.ACCEPTED_CLIENTS,
        )
        _require_unique_ordered(
            self.excluded_client_ids,
            PopulationManifestField.EXCLUDED_CLIENT_IDS,
        )
        _require_client_set_partition(
            self.candidate_clients,
            self.accepted_clients,
            self.excluded_client_ids,
        )
        _require_non_negative_row_counts(
            self.total_membership_rows,
            self.benign_row_count,
            self.attack_row_count,
        )
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
        if reduce(RowCount.plus, counts) != self.assignment_row_count:
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
    observed_eligible_group_count: NonNegativeIntegerValue
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
        if (
            min(
                self.duplicate_timestamp_rows.value,
                self.total_temporal_rows.value,
                self.observed_eligible_group_count.value,
            )
            < 0
        ):
            raise ValueError("chronology diagnostic counts must be non-negative")
        return self


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
        return (
            self.population.value,
            self.identity_kind.value,
            self.client_id,
        ) < (
            other.population.value,
            other.identity_kind.value,
            other.client_id,
        )


@dataclass(frozen=True, slots=True)
class ClientPartitionCounts:
    """Per-client partition support counts used to construct evaluation cohorts."""

    client: ClientIdentity
    benign_calibration_count: RowCount
    benign_evaluation_count: RowCount
    attack_evaluation_count: RowCount
    accepted: bool
    deployment_fallback: bool

    def __post_init__(self) -> None:
        if not isinstance(self.client, ClientIdentity):
            raise TypeError("client partition counts require a ClientIdentity")


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
    observed_client_count: NonNegativeIntegerValue
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
    """Typed request boundary for non-temporal, temporal, and static-reference splits."""

    membership: pl.DataFrame
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    population_manifest_checksum: Checksum
    capture_timestamp_column: CaptureTimestampColumn | None = None


@dataclass(frozen=True, slots=True, eq=False)
class MatchedReferencePopulation:
    """A secondary population constructed over the same accepted rows as a primary population."""

    manifest: PopulationManifest
    membership: pl.DataFrame


@dataclass(frozen=True, slots=True, eq=False)
class PopulationConstructionEvidence:
    """Typed per-row and per-client evidence produced alongside a population construction."""

    excluded_rows: pl.DataFrame
    client_eligibility: pl.DataFrame


@dataclass(slots=True, eq=False)
class PopulationConstructionResult:
    manifest: PopulationManifest
    membership: pl.DataFrame
    diagnostics: DirichletPartitionDiagnosticsDocument | ChronologicalPartitionDiagnosticsDocument | None
    matched_reference: MatchedReferencePopulation | None = None
    evidence: PopulationConstructionEvidence | None = None

    @property
    def population(self) -> PopulationId:
        return self.manifest.document.population


@dataclass(frozen=True, slots=True)
class PopulationConstructionRequest:
    population_id: PopulationId
    canonical_root: Path
    partition_seed: Seed
    split_protocol: SplitProtocolId
    dirichlet_condition: ControlledPartitionCondition | None


@dataclass(frozen=True, slots=True)
class PreprocessingHandoffRequest:
    construction: PopulationConstructionResult
    deployment_fallback_client_ids: frozenset[str]
    capture_timestamp_column: CaptureTimestampColumn | None = None


@dataclass(slots=True, eq=False)
class PreprocessingHandoff:
    """Typed boundary from dataset partitioning into preprocessing."""

    population_manifest: PopulationManifest
    membership: pl.DataFrame
    assignments: pl.DataFrame
    client_partition_counts: tuple[ClientPartitionCounts, ...]
    deployment_fallback_client_ids: frozenset[ClientIdentity] = frozenset()


def dirichlet_condition(
    concentration: DirichletConcentration,
) -> ControlledPartitionCondition:
    return ControlledPartitionCondition(
        ControlledPartitionKind.DIRICHLET,
        concentration,
    )


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
        client_identities(
            document.population,
            document.candidate_clients,
            document.identity_kind,
        ),
        feasibility,
        family_by_client,
    )


def synthetic_client_ids(client_count: ClientCount) -> tuple[str, ...]:
    width = max(2, len(str(client_count.value - 1)))
    return tuple(f"synthetic_client_{index:0{width}d}" for index in range(client_count.value))


def membership_checksum(
    client_ids: tuple[str, ...],
    stable_row_ids: tuple[str, ...],
) -> Checksum:
    payload = "\n".join((*client_ids, *stable_row_ids))
    return checksum_text(payload)


def population_evidence_role(population_id: PopulationId) -> EvidenceRole:
    """Primary scientific role of the population (not the only permitted claim tier)."""
    match population_id:
        case PopulationId.NBAIOT_NATURAL_DEVICES:
            return EvidenceRole.CONFIRMATORY
        case PopulationId.NBAIOT_DIRICHLET_CLIENTS:
            return EvidenceRole.MECHANISM
        case PopulationId.CICIOT_FILE_CLIENTS:
            return EvidenceRole.APPLICABILITY_BOUNDARY
        case PopulationId.EDGE_SENSOR_GROUPS:
            return EvidenceRole.EXTERNAL_VALIDATION
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            return EvidenceRole.TEMPORAL_BOUNDARY


def population_allowed_evidence_roles(population_id: PopulationId) -> frozenset[EvidenceRole]:
    """Claim tiers authorized on a population without forcing every artifact to the primary role.

    N-BaIoT natural devices host confirmatory, supportive, mechanism, threshold-variant,
    stress-test, operational, exploratory, and anchor studies. The primary role remains
    confirmatory; evaluation must accept any authorized experiment role.
    """
    match population_id:
        case PopulationId.NBAIOT_NATURAL_DEVICES:
            return frozenset(
                {
                    EvidenceRole.ANCHOR_REPRODUCTION,
                    EvidenceRole.CONFIRMATORY,
                    EvidenceRole.SUPPORTIVE,
                    EvidenceRole.MECHANISM,
                    EvidenceRole.THRESHOLD_VARIANT,
                    EvidenceRole.TRAINING_STRESS_TEST,
                    EvidenceRole.OPERATIONAL_TRANSLATION,
                    EvidenceRole.EXPLORATORY,
                }
            )
        case PopulationId.NBAIOT_DIRICHLET_CLIENTS:
            return frozenset({EvidenceRole.MECHANISM, EvidenceRole.SUPPORTIVE, EvidenceRole.EXPLORATORY})
        case PopulationId.CICIOT_FILE_CLIENTS:
            return frozenset({EvidenceRole.APPLICABILITY_BOUNDARY})
        case PopulationId.EDGE_SENSOR_GROUPS:
            return frozenset({EvidenceRole.EXTERNAL_VALIDATION, EvidenceRole.SUPPORTIVE})
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            return frozenset({EvidenceRole.TEMPORAL_BOUNDARY})


def build_population_capabilities(
    declaration: PopulationDeclaration,
    evidentiary_role: EvidenceRole,
    dataset_capabilities: DatasetCapabilities,
) -> PopulationCapabilities:
    """Compose a population's capability profile from its declaration and owning dataset capabilities."""
    _require_population_allowed(declaration, dataset_capabilities)
    return PopulationCapabilities(
        population=declaration.id,
        dataset=declaration.dataset,
        identity_kind=declaration.identity_kind,
        declared_client_count=declaration.client_count,
        physical_client_validity=_physical_validity(declaration, dataset_capabilities),
        family_taxonomy=_family_status(declaration, dataset_capabilities),
        chronology=_chronology_status(declaration, dataset_capabilities),
        client_level_attack_assignment=_attack_status(declaration, dataset_capabilities),
        fpr_evaluation=_fpr_status(dataset_capabilities),
        attack_sensitive_evaluation=_attack_metric_status(declaration, dataset_capabilities),
        temporal_support=_temporal_status(declaration, dataset_capabilities),
        valid_threshold_methods=_threshold_methods(declaration, dataset_capabilities),
        evidentiary_role=evidentiary_role,
        confirmatory_eligible=declaration.is_confirmatory_population,
    )


def _require_population_allowed(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> None:
    if declaration.id not in capabilities.valid_populations:
        raise CapabilityError(
            "population is not valid for its dataset",
            subject=declaration.id,
            reason="dataset capability catalogue does not list the population",
        )


def _physical_validity(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    match declaration.identity_kind:
        case PopulationIdentityKind.PHYSICAL_DEVICES:
            return capabilities.physical_clients.status
        case PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS:
            return CapabilityStatus.NOT_APPLICABLE
        case PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS:
            return capabilities.physical_clients.status
        case PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS:
            return CapabilityStatus.NOT_APPLICABLE
        case PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS:
            return capabilities.physical_clients.status


def _family_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_family_taxonomy:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.family_taxonomy.status


def _chronology_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_verified_chronology:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.chronology.status


def _attack_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_client_attack_assignment:
        return CapabilityStatus.UNAVAILABLE
    if not capabilities.attack_assignment.client_level_assignment_available:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.attack_assignment.status


def _fpr_status(capabilities: DatasetCapabilities) -> CapabilityStatus:
    return capabilities.metrics.status_for(MetricId.FALSE_POSITIVE_RATE)


def _attack_metric_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_client_attack_assignment:
        return CapabilityStatus.UNAVAILABLE
    if not capabilities.attack_assignment.client_level_assignment_available:
        return CapabilityStatus.UNAVAILABLE
    statuses = frozenset(
        capabilities.metrics.status_for(metric)
        for metric in (
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BALANCED_ACCURACY,
            MetricId.BINARY_MACRO_F1,
            MetricId.AUROC,
        )
    )
    if statuses == {CapabilityStatus.SUPPORTED}:
        return CapabilityStatus.SUPPORTED
    if CapabilityStatus.CONDITIONAL in statuses:
        return CapabilityStatus.CONDITIONAL
    return CapabilityStatus.UNAVAILABLE


def _temporal_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_verified_chronology:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.temporal.status


def _threshold_methods(
    declaration: PopulationDeclaration, capabilities: DatasetCapabilities
) -> tuple[FederatedThresholdMethod, ...]:
    supported = tuple(
        item.method
        for item in capabilities.threshold_methods
        if item.status in {CapabilityStatus.SUPPORTED, CapabilityStatus.CONDITIONAL}
    )
    if declaration.requires_family_taxonomy and FederatedThresholdMethod.FAMILY_THRESHOLD not in supported:
        if capabilities.family_taxonomy.status is CapabilityStatus.SUPPORTED:
            return supported + (FederatedThresholdMethod.FAMILY_THRESHOLD,)
    if not declaration.requires_family_taxonomy:
        return tuple(method for method in supported if method is not FederatedThresholdMethod.FAMILY_THRESHOLD)
    return supported


def _require_unique_ordered(
    values: tuple[str, ...],
    field: PopulationManifestField,
) -> None:
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


def _require_non_negative_row_counts(
    total: RowCount,
    benign: RowCount,
    attack: RowCount,
) -> None:
    if benign.plus(attack) != total:
        raise ValueError("benign and attack rows must sum to total membership rows")


def _require_client_series_shape(
    document: DirichletPartitionDiagnosticsDocument,
) -> None:
    expected = document.client_count.value
    if len(document.client_ids) != expected:
        raise ValueError("client identity count must match declared client count")
    for series in (
        document.client_row_counts,
        document.benign_row_counts,
        document.attack_row_counts,
    ):
        if len(series) != expected:
            raise ValueError("per-client count series must be complete")


def _require_row_conservation(
    document: DirichletPartitionDiagnosticsDocument,
) -> None:
    if reduce(RowCount.plus, document.client_row_counts, RowCount(0)) != document.total_rows:
        raise ValueError("client row counts must conserve total rows")
    benign_total = reduce(RowCount.plus, document.benign_row_counts, RowCount(0))
    attack_total = reduce(RowCount.plus, document.attack_row_counts, RowCount(0))
    if benign_total.plus(attack_total) != document.total_rows:
        raise ValueError("benign and attack counts must conserve total rows")


def _require_partition_kind_fields(
    document: DirichletPartitionDiagnosticsDocument,
) -> None:
    match document.partition_kind:
        case ControlledPartitionKind.DIRICHLET:
            if document.concentration is None:
                raise ValueError("Dirichlet diagnostics require a positive concentration")
        case ControlledPartitionKind.IID:
            if document.concentration is not None:
                raise ValueError("IID diagnostics must not carry a Dirichlet concentration")
