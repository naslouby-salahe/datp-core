from dataclasses import dataclass
from enum import StrEnum
from functools import reduce, total_ordering
from pathlib import Path

import polars as pl
from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    CapabilityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CaptureTimestampColumn,
    ChronologyGroupIdentity,
    ClientIdentityToken,
    ColumnName,
    ContractSubject,
    DatasetId,
    EvidenceRole,
    FamilyIdentity,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
    StableRowId,
    ValidationReasonText,
)
from datp_core.core.numeric import (
    ClientCount,
    DirichletConcentration,
    NonNegativeIntegerValue,
    RowCount,
    Seed,
)


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONDITIONAL = "conditional"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class CapabilityStatement:
    status: CapabilityStatus
    evidence: ValidationReasonText
    reason: ValidationReasonText

    def __post_init__(self) -> None:
        if not self.evidence.strip() or not self.reason.strip():
            raise ValueError("capability statements require evidence and a reason")


@dataclass(frozen=True, slots=True)
class PhysicalClientCapability(CapabilityStatement):
    identities: tuple[ClientIdentityToken, ...]


@dataclass(frozen=True, slots=True)
class FamilyTaxonomyCapability(CapabilityStatement):
    families: tuple[FamilyIdentity, ...]


@dataclass(frozen=True, slots=True)
class ChronologyCapability(CapabilityStatement):
    temporal_group_identities: tuple[ChronologyGroupIdentity, ...]


@dataclass(frozen=True, slots=True)
class AttackAssignmentCapability(CapabilityStatement):
    row_level_labels_available: bool
    client_level_assignment_available: bool


@dataclass(frozen=True, slots=True)
class MetricCapability(CapabilityStatement):
    available_metrics: tuple[MetricId, ...]
    conditional_metrics: tuple[MetricId, ...]
    unavailable_metrics: tuple[MetricId, ...]

    def __post_init__(self) -> None:
        CapabilityStatement.__post_init__(self)
        groups = (self.available_metrics, self.conditional_metrics, self.unavailable_metrics)
        declared = tuple(metric for group in groups for metric in group)
        if not declared or len(declared) != len(frozenset(declared)):
            raise ValueError("metric capabilities must declare non-overlapping metrics")
        statuses = frozenset(
            status
            for metrics, status in (
                (self.available_metrics, CapabilityStatus.SUPPORTED),
                (self.conditional_metrics, CapabilityStatus.CONDITIONAL),
                (self.unavailable_metrics, CapabilityStatus.UNAVAILABLE),
            )
            if metrics
        )
        aggregate = (
            CapabilityStatus.SUPPORTED
            if statuses == frozenset({CapabilityStatus.SUPPORTED})
            else CapabilityStatus.UNAVAILABLE
        )
        if len(statuses) > 1 or CapabilityStatus.CONDITIONAL in statuses:
            aggregate = CapabilityStatus.CONDITIONAL
        if self.status is not aggregate:
            raise ValueError("metric capability status must match its explicit metric declarations")

    def status_for(self, metric: MetricId) -> CapabilityStatus:
        if metric in self.available_metrics:
            return CapabilityStatus.SUPPORTED
        if metric in self.conditional_metrics:
            return CapabilityStatus.CONDITIONAL
        return CapabilityStatus.UNAVAILABLE


@dataclass(frozen=True, slots=True)
class TemporalCapability(CapabilityStatement):
    supports_one_shot_recalibration: bool


@dataclass(frozen=True, slots=True)
class ExternalValidationCapability(CapabilityStatement):
    roles: tuple[EvidenceRole, ...]


@dataclass(frozen=True, slots=True)
class ThresholdMethodCapability(CapabilityStatement):
    method: FederatedThresholdMethod


@dataclass(frozen=True, slots=True)
class DatasetCapabilities:
    physical_clients: PhysicalClientCapability
    family_taxonomy: FamilyTaxonomyCapability
    chronology: ChronologyCapability
    attack_assignment: AttackAssignmentCapability
    metrics: MetricCapability
    temporal: TemporalCapability
    external_validation: ExternalValidationCapability
    valid_populations: tuple[PopulationId, ...]
    threshold_methods: tuple[ThresholdMethodCapability, ...]

    def __post_init__(self) -> None:
        if not self.valid_populations:
            raise ValueError("dataset capabilities require valid populations")
        if len(self.valid_populations) != len(frozenset(self.valid_populations)):
            raise ValueError("dataset capability populations must be unique")
        methods = tuple(capability.method for capability in self.threshold_methods)
        if len(methods) != len(frozenset(methods)):
            raise ValueError("threshold method capabilities must be unique")


class CanonicalProvenanceColumn(StrEnum):
    SOURCE_ROW_INDEX = "source_row_index"
    SOURCE_PATH = "source_path"
    STABLE_ROW_ID = "stable_row_id"


class ControlledPartitionKind(StrEnum):
    DIRICHLET = "dirichlet"
    IID = "iid"


class PopulationOutcomeLabel(StrEnum):
    BENIGN = "benign"
    ATTACK = "attack"


class PopulationFrameColumn(StrEnum):
    CLIENT_ID = "client_id"
    OUTCOME_LABEL = "outcome_label"
    PARTITION_ROLE = "partition_role"
    FAMILY_ID = "family_id"
    STABLE_ROW_ID = CanonicalProvenanceColumn.STABLE_ROW_ID.value
    SOURCE_PATH = CanonicalProvenanceColumn.SOURCE_PATH.value
    SOURCE_ROW_INDEX = CanonicalProvenanceColumn.SOURCE_ROW_INDEX.value


class PopulationManifestField(StrEnum):
    CANDIDATE_CLIENTS = "candidate_clients"
    ACCEPTED_CLIENTS = "accepted_clients"
    EXCLUDED_CLIENT_IDS = "excluded_client_ids"
    TOTAL_MEMBERSHIP_ROWS = "total_membership_rows"
    BENIGN_ROW_COUNT = "benign_row_count"
    ATTACK_ROW_COUNT = "attack_row_count"


class WorkingFrameColumn(StrEnum):
    ORDER = "_order"
    PERM = "_perm"
    MAX_HISTORICAL = "max_historical_timestamp"
    MIN_FUTURE = "min_future_timestamp"


class CohortAggregationColumn(StrEnum):
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


def membership_column_names() -> tuple[ColumnName, ...]:
    return tuple(ColumnName(column.value) for column in MEMBERSHIP_COLUMNS)


def assignment_column_names() -> tuple[ColumnName, ...]:
    return tuple(ColumnName(column.value) for column in ASSIGNMENT_COLUMNS)


def select_membership_frame(frame: pl.DataFrame) -> pl.DataFrame:
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
    CANONICAL_CHRONOLOGY_MISSING = "canonical_chronology_missing"
    CANONICAL_CHRONOLOGY_INELIGIBLE = "canonical_chronology_ineligible"
    MODBUS_ADDRESS_LITERAL = "modbus_address_literal"


class ModelInputExclusionReason(StrEnum):
    NONFINITE_OR_NULL_NUMERIC_MODEL_INPUT_FEATURE = "nonfinite_or_null_numeric_model_input_feature"


class ModelInputExclusionEvidence(StrictModel):
    dataset: DatasetId
    population: PopulationId
    reason: ModelInputExclusionReason
    total_row_count: RowCount
    excluded_row_count: RowCount
    excluded_stable_row_ids: tuple[StableRowId, ...]

    @model_validator(mode="after")
    def validate_exclusion_evidence(self) -> "ModelInputExclusionEvidence":
        if self.excluded_row_count.value != len(self.excluded_stable_row_ids):
            raise ValueError("excluded row count must match stable-row provenance")
        if self.total_row_count.value < self.excluded_row_count.value:
            raise ValueError("excluded row count cannot exceed total candidate rows")
        if tuple(sorted(self.excluded_stable_row_ids)) != self.excluded_stable_row_ids:
            raise ValueError("excluded stable-row identities must be sorted")
        if len(set(self.excluded_stable_row_ids)) != len(self.excluded_stable_row_ids):
            raise ValueError("excluded stable-row identities must be unique")
        return self


class PopulationManifestDocument(StrictModel):
    population: PopulationId
    dataset: DatasetId
    identity_kind: PopulationIdentityKind
    partition_seed: Seed
    split_protocol: SplitProtocolId
    candidate_clients: tuple[ClientIdentityToken, ...]
    accepted_clients: tuple[ClientIdentityToken, ...]
    excluded_client_ids: tuple[ClientIdentityToken, ...]
    total_membership_rows: RowCount
    benign_row_count: RowCount
    attack_row_count: RowCount
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
    discarded_row_count: RowCount

    @model_validator(mode="after")
    def validate_manifest(self) -> "SplitManifestDocument":
        counts = (
            self.train_row_count,
            self.calibration_row_count,
            self.evaluation_row_count,
            self.future_recalibration_row_count,
            self.static_reference_reserve_row_count,
            self.discarded_row_count,
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
    client_ids: tuple[ClientIdentityToken, ...]
    total_rows: RowCount
    client_row_counts: tuple[RowCount, ...]
    benign_row_counts: tuple[RowCount, ...]
    attack_row_counts: tuple[RowCount, ...]
    empty_client_ids: tuple[ClientIdentityToken, ...]
    insufficient_benign_client_ids: tuple[ClientIdentityToken, ...]

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
    eligible_group_ids: tuple[ChronologyGroupIdentity, ...]
    excluded_group_ids: tuple[ChronologyGroupIdentity, ...]
    exclusion_reasons: tuple[ChronologyExclusionReason, ...]
    duplicate_timestamp_rows: RowCount
    total_temporal_rows: RowCount

    @model_validator(mode="after")
    def validate_diagnostics(self) -> "ChronologicalPartitionDiagnosticsDocument":
        if self.observed_eligible_group_count.value != len(self.eligible_group_ids):
            raise ValueError("observed eligible count must match eligible identities")
        if len(self.excluded_group_ids) != len(self.exclusion_reasons):
            raise ValueError("each excluded group requires one typed reason")
        return self


@total_ordering
@dataclass(frozen=True, slots=True)
class ClientIdentity:
    population: PopulationId
    client_id: ClientIdentityToken
    identity_kind: PopulationIdentityKind

    def __post_init__(self) -> None:
        if any(separator in self.client_id.value for separator in ("=", "/", "\\")):
            raise ValueError("client identity must be a path-safe token")

    def __lt__(self, other: "ClientIdentity") -> bool:
        return (
            self.population.value,
            self.identity_kind.value,
            self.client_id.value,
        ) < (
            other.population.value,
            other.identity_kind.value,
            other.client_id.value,
        )


@dataclass(frozen=True, slots=True)
class FamilyAssignment:
    client: ClientIdentity
    family: FamilyIdentity

    @property
    def population(self) -> PopulationId:
        return self.client.population


@dataclass(frozen=True, slots=True)
class EligibleCohort:
    clients: tuple[ClientIdentity, ...]

    def __post_init__(self) -> None:
        if not self.clients:
            raise ScientificContractError(
                ErrorMessage("eligible cohort must contain at least one client"), subject=ContractSubject.CALIBRATION
            )
        if tuple(sorted(self.clients)) != self.clients:
            raise ScientificContractError(
                ErrorMessage("eligible cohort must preserve deterministic client ordering"),
                subject=ContractSubject.CLIENT,
            )
        if len(frozenset(self.clients)) != len(self.clients):
            raise ScientificContractError(
                ErrorMessage("eligible cohort clients must be unique"), subject=ContractSubject.CLIENT
            )

    def __len__(self) -> int:
        return len(self.clients)

    def __iter__(self):
        return iter(self.clients)

    def __contains__(self, client: ClientIdentity) -> bool:
        return client in frozenset(self.clients)


@dataclass(frozen=True, slots=True)
class ClientPartitionCounts:
    client: ClientIdentity
    benign_calibration_count: RowCount
    benign_evaluation_count: RowCount
    attack_evaluation_count: RowCount
    accepted: bool
    deployment_fallback: bool


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
    evidence: ValidationReasonText

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("feasibility requires evidence")


@dataclass(frozen=True, slots=True)
class PopulationManifest:
    document: PopulationManifestDocument
    clients: tuple[ClientIdentity, ...]
    feasibility: PopulationFeasibility
    family_by_client: tuple[FamilyAssignment, ...]

    def __post_init__(self) -> None:
        _require_manifest_clients(self.clients, self.document.candidate_clients)
        _require_manifest_family_assignments(self.clients, self.family_by_client)


def _require_manifest_clients(
    clients: tuple[ClientIdentity, ...], candidate_client_ids: tuple[ClientIdentityToken, ...]
) -> None:
    if tuple(client.client_id for client in clients) != candidate_client_ids:
        raise ValueError("manifest clients must match candidate client identities in order")


def _require_manifest_family_assignments(
    clients: tuple[ClientIdentity, ...], family_assignments: tuple[FamilyAssignment, ...]
) -> None:
    assigned_clients = tuple(assignment.client for assignment in family_assignments)
    if len(assigned_clients) != len(frozenset(assigned_clients)):
        raise ValueError("manifest family assignments must have unique clients")
    if not frozenset(assigned_clients).issubset(frozenset(clients)):
        raise ValueError("manifest family assignments must belong to manifest clients")


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
    membership: pl.DataFrame
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    capture_timestamp_column: CaptureTimestampColumn | None = None


@dataclass(frozen=True, slots=True, eq=False)
class MatchedReferencePopulation:
    manifest: PopulationManifest
    membership: pl.DataFrame


@dataclass(frozen=True, slots=True, eq=False)
class PopulationConstructionEvidence:
    excluded_rows: pl.DataFrame
    client_eligibility: pl.DataFrame


@dataclass(slots=True, eq=False)
class PopulationConstructionResult:
    manifest: PopulationManifest
    membership: pl.DataFrame
    diagnostics: DirichletPartitionDiagnosticsDocument | ChronologicalPartitionDiagnosticsDocument | None
    matched_reference: MatchedReferencePopulation | None = None
    evidence: PopulationConstructionEvidence | None = None
    model_input_exclusions: ModelInputExclusionEvidence | None = None

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
    deployment_fallback_client_ids: frozenset[ClientIdentityToken]
    capture_timestamp_column: CaptureTimestampColumn | None = None


@dataclass(slots=True, eq=False)
class PreprocessingHandoff:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    assignments: pl.DataFrame
    client_partition_counts: tuple[ClientPartitionCounts, ...]
    deployment_fallback_client_ids: frozenset[ClientIdentity] = frozenset()


@dataclass(frozen=True, slots=True)
class PopulationDeclaration:
    id: PopulationId
    dataset: DatasetId
    identity_kind: PopulationIdentityKind
    client_count: ClientCount
    requires_family_taxonomy: bool
    requires_verified_chronology: bool
    requires_client_attack_assignment: bool
    is_confirmatory_population: bool


def dirichlet_condition(concentration: DirichletConcentration) -> ControlledPartitionCondition:
    return ControlledPartitionCondition(ControlledPartitionKind.DIRICHLET, concentration)


def iid_condition() -> ControlledPartitionCondition:
    return ControlledPartitionCondition(ControlledPartitionKind.IID, None)


def client_identities(
    population: PopulationId,
    client_ids: tuple[ClientIdentityToken, ...],
    identity_kind: PopulationIdentityKind,
) -> tuple[ClientIdentity, ...]:
    return tuple(ClientIdentity(population, client_id, identity_kind) for client_id in client_ids)


def build_population_manifest(
    document: PopulationManifestDocument,
    feasibility: PopulationFeasibility,
    family_by_client: tuple[FamilyAssignment, ...] = (),
) -> PopulationManifest:
    return PopulationManifest(
        document,
        client_identities(document.population, document.candidate_clients, document.identity_kind),
        feasibility,
        family_by_client,
    )


def synthetic_client_ids(client_count: ClientCount) -> tuple[ClientIdentityToken, ...]:
    width = max(2, len(str(client_count.value - 1)))
    return tuple(ClientIdentityToken(f"synthetic_client_{index:0{width}d}") for index in range(client_count.value))


def population_evidence_role(population_id: PopulationId) -> EvidenceRole:
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


class PopulationCapabilityViolation(StrEnum):
    POPULATION_NOT_IN_CATALOGUE = "population_not_in_catalogue"


class TemporalSplitViolation(StrEnum):
    CAPTURE_TIMESTAMP_UNAVAILABLE = "capture_timestamp_unavailable"


def _require_population_allowed(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> None:
    if declaration.id not in capabilities.valid_populations:
        raise CapabilityError(
            ErrorMessage("population is not valid for its dataset"),
            subject=declaration.id,
            reason=PopulationCapabilityViolation.POPULATION_NOT_IN_CATALOGUE,
        )


def _physical_validity(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    match declaration.identity_kind:
        case PopulationIdentityKind.PHYSICAL_DEVICES:
            return capabilities.physical_clients.status
        case PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS | PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS:
            return CapabilityStatus.NOT_APPLICABLE
        case PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS | PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS:
            return capabilities.physical_clients.status


def _family_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    return capabilities.family_taxonomy.status if declaration.requires_family_taxonomy else CapabilityStatus.UNAVAILABLE


def _chronology_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    return capabilities.chronology.status if declaration.requires_verified_chronology else CapabilityStatus.UNAVAILABLE


def _attack_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if (
        not declaration.requires_client_attack_assignment
        or not capabilities.attack_assignment.client_level_assignment_available
    ):
        return CapabilityStatus.UNAVAILABLE
    return capabilities.attack_assignment.status


def _fpr_status(capabilities: DatasetCapabilities) -> CapabilityStatus:
    return capabilities.metrics.status_for(MetricId.FALSE_POSITIVE_RATE)


def _attack_metric_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if (
        not declaration.requires_client_attack_assignment
        or not capabilities.attack_assignment.client_level_assignment_available
    ):
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
    if statuses == frozenset({CapabilityStatus.SUPPORTED}):
        return CapabilityStatus.SUPPORTED
    if CapabilityStatus.CONDITIONAL in statuses:
        return CapabilityStatus.CONDITIONAL
    return CapabilityStatus.UNAVAILABLE


def _temporal_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    return capabilities.temporal.status if declaration.requires_verified_chronology else CapabilityStatus.UNAVAILABLE


def _threshold_methods(
    declaration: PopulationDeclaration,
    capabilities: DatasetCapabilities,
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


def _require_unique_ordered(values: tuple[ClientIdentityToken, ...], field: PopulationManifestField) -> None:
    if len(values) != len(frozenset(values)):
        raise ValueError(f"{field.value} must be unique")


def _require_client_set_partition(
    candidates: tuple[ClientIdentityToken, ...],
    accepted: tuple[ClientIdentityToken, ...],
    excluded: tuple[ClientIdentityToken, ...],
) -> None:
    accepted_set = frozenset(accepted)
    if not accepted_set <= frozenset(candidates):
        raise ValueError(f"{PopulationManifestField.ACCEPTED_CLIENTS.value} must be a subset of candidates")
    if frozenset(excluded) & accepted_set:
        raise ValueError(f"{PopulationManifestField.EXCLUDED_CLIENT_IDS.value} cannot also be accepted")


def _require_non_negative_row_counts(total: RowCount, benign: RowCount, attack: RowCount) -> None:
    if benign.plus(attack) != total:
        raise ValueError("benign and attack rows must sum to total membership rows")


def _require_client_series_shape(document: DirichletPartitionDiagnosticsDocument) -> None:
    expected = document.client_count.value
    if len(document.client_ids) != expected:
        raise ValueError("client identity count must match declared client count")
    for series in (document.client_row_counts, document.benign_row_counts, document.attack_row_counts):
        if len(series) != expected:
            raise ValueError("per-client count series must be complete")


def _require_row_conservation(document: DirichletPartitionDiagnosticsDocument) -> None:
    if reduce(RowCount.plus, document.client_row_counts, RowCount(0)) != document.total_rows:
        raise ValueError("client row counts must conserve total rows")
    benign_total = reduce(RowCount.plus, document.benign_row_counts, RowCount(0))
    attack_total = reduce(RowCount.plus, document.attack_row_counts, RowCount(0))
    if benign_total.plus(attack_total) != document.total_rows:
        raise ValueError("benign and attack counts must conserve total rows")


def _require_partition_kind_fields(document: DirichletPartitionDiagnosticsDocument) -> None:
    match document.partition_kind:
        case ControlledPartitionKind.DIRICHLET:
            if document.concentration is None:
                raise ValueError("Dirichlet diagnostics require a positive concentration")
        case ControlledPartitionKind.IID:
            if document.concentration is not None:
                raise ValueError("IID diagnostics must not carry a Dirichlet concentration")


DIRICHLET_CONCENTRATIONS = tuple(DirichletConcentration(value) for value in (0.1, 0.3, 0.5, 1.0, 10.0))
NBAIOT_NATURAL_DEVICE_COUNT = ClientCount(9)
NBAIOT_DIRICHLET_CLIENT_COUNT = ClientCount(20)
CICIOT_FILE_CLIENT_COUNT = ClientCount(63)
EDGE_STATIC_SENSOR_GROUP_COUNT = ClientCount(10)
EDGE_TEMPORAL_SENSOR_GROUP_COUNT = ClientCount(9)

NBAIOT_NATURAL_DEVICES = PopulationDeclaration(
    id=PopulationId.NBAIOT_NATURAL_DEVICES,
    dataset=DatasetId.NBAIOT,
    identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
    client_count=NBAIOT_NATURAL_DEVICE_COUNT,
    requires_family_taxonomy=True,
    requires_verified_chronology=False,
    requires_client_attack_assignment=True,
    is_confirmatory_population=True,
)
CICIOT_FILE_CLIENTS = PopulationDeclaration(
    id=PopulationId.CICIOT_FILE_CLIENTS,
    dataset=DatasetId.CICIOT2023,
    identity_kind=PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS,
    client_count=CICIOT_FILE_CLIENT_COUNT,
    requires_family_taxonomy=False,
    requires_verified_chronology=False,
    requires_client_attack_assignment=False,
    is_confirmatory_population=False,
)
NBAIOT_DIRICHLET_CLIENTS = PopulationDeclaration(
    id=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
    dataset=DatasetId.NBAIOT,
    identity_kind=PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
    client_count=NBAIOT_DIRICHLET_CLIENT_COUNT,
    requires_family_taxonomy=False,
    requires_verified_chronology=False,
    requires_client_attack_assignment=True,
    is_confirmatory_population=False,
)
EDGE_SENSOR_GROUPS = PopulationDeclaration(
    id=PopulationId.EDGE_SENSOR_GROUPS,
    dataset=DatasetId.EDGE_IIOTSET,
    identity_kind=PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
    client_count=EDGE_STATIC_SENSOR_GROUP_COUNT,
    requires_family_taxonomy=False,
    requires_verified_chronology=False,
    requires_client_attack_assignment=False,
    is_confirmatory_population=False,
)
EDGE_TEMPORAL_GROUPS = PopulationDeclaration(
    id=PopulationId.EDGE_TEMPORAL_GROUPS,
    dataset=DatasetId.EDGE_IIOTSET,
    identity_kind=PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
    client_count=EDGE_TEMPORAL_SENSOR_GROUP_COUNT,
    requires_family_taxonomy=False,
    requires_verified_chronology=True,
    requires_client_attack_assignment=False,
    is_confirmatory_population=False,
)
POPULATIONS = (
    NBAIOT_NATURAL_DEVICES,
    CICIOT_FILE_CLIENTS,
    NBAIOT_DIRICHLET_CLIENTS,
    EDGE_SENSOR_GROUPS,
    EDGE_TEMPORAL_GROUPS,
)
