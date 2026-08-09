"""Population, split, cohort, and chronology integrity invariants."""

from collections.abc import Iterable
from enum import StrEnum

import polars as pl

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    DataIntegrityError,
    ErrorMessage,
    LeakageError,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CaptureTimestampColumn,
    ClientIdentityToken,
    ColumnName,
    ContractSubject,
    PartitionRole,
    PopulationId,
    StableRowId,
    StageOperationId,
    ValidationReasonText,
)
from datp_core.core.numeric import ClientCount, RowCount
from datp_core.data.populations.contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationCapabilities,
    PopulationDeclaration,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationOutcomeLabel,
    SplitManifestDocument,
    WorkingFrameColumn,
    assignment_column_names,
    membership_checksum,
    membership_column_names,
)

_BENIGN = PopulationOutcomeLabel.BENIGN
_ATTACK = PopulationOutcomeLabel.ATTACK
_MAX_HIST = WorkingFrameColumn.MAX_HISTORICAL
_MIN_FUT = WorkingFrameColumn.MIN_FUTURE


class PopulationIntegrityViolation(StrEnum):
    CAPABILITY_POPULATION_MISMATCH = "capability_population_mismatch"
    MISSING_CAPTURE_TIMESTAMPS = "missing_capture_timestamps"
    DIRICHLET_SOURCE_ROWS_NOT_CONSERVED = "dirichlet_source_rows_not_conserved"
    DIRICHLET_DUPLICATE_STABLE_ROW_IDENTITIES = "dirichlet_duplicate_stable_row_identities"
    DIRICHLET_CLIENT_COUNT_EXCEEDED = "dirichlet_client_count_exceeded"
    MEMBERSHIP_ROW_COUNT_MISMATCH = "membership_row_count_mismatch"
    MEMBERSHIP_DUPLICATE_STABLE_ROW_IDENTITIES = "membership_duplicate_stable_row_identities"
    MEMBERSHIP_CLIENTS_NOT_ACCEPTED = "membership_clients_not_accepted"
    MEMBERSHIP_EMPTY_WITH_NONZERO_MANIFEST = "membership_empty_with_nonzero_manifest"
    CANDIDATE_CLIENT_COUNT_MISMATCH = "candidate_client_count_mismatch"
    ASSIGNMENT_ROW_COUNT_MISMATCH = "assignment_row_count_mismatch"
    ASSIGNMENT_ROWS_NOT_CONSERVED = "assignment_rows_not_conserved"
    ASSIGNMENT_DUPLICATE_STABLE_ROW_IDENTITIES = "assignment_duplicate_stable_row_identities"
    ROLE_COUNT_MISMATCH = "role_count_mismatch"
    ATTACK_ROWS_IN_FIT_ROLES = "attack_rows_in_fit_roles"
    FUTURE_PRECEDES_HISTORICAL = "future_precedes_historical"
    OUTCOME_COUNT_MISMATCH = "outcome_count_mismatch"
    MISSING_REQUIRED_COLUMNS = "missing_required_columns"


def reject_non_benign_labels(
    labels: Iterable[PopulationOutcomeLabel],
    *,
    message: ValidationReasonText,
    subject: ContractSubject,
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN,
) -> None:
    if any(label != benign_label for label in labels):
        raise LeakageError(ErrorMessage(message), subject=subject)


def membership_frame_checksum(membership: pl.DataFrame) -> Checksum:
    return membership_checksum(
        tuple(ClientIdentityToken(c) for c in membership.get_column(CLIENT_ID_COLUMN).to_list()),
        tuple(StableRowId(row) for row in membership.get_column(STABLE_ROW_ID_COLUMN).to_list()),
    )


def outcome_row_counts(membership: pl.DataFrame) -> tuple[RowCount, RowCount]:
    benign = int(membership.filter(pl.col(OUTCOME_LABEL_COLUMN) == _BENIGN).height)
    return RowCount(benign), RowCount(membership.height - benign)


def validate_population_manifest(
    manifest: PopulationManifest,
    membership: pl.DataFrame,
    declaration: PopulationDeclaration,
    capabilities: PopulationCapabilities,
) -> None:
    document = manifest.document
    _require_columns(membership, membership_column_names(), StageOperationId.CONSTRUCT_POPULATION)
    _require_membership_row_contract(membership, document.total_membership_rows, document.population)
    _require_membership_client_subset(membership, document.accepted_clients, document.population)
    _require_candidate_count(document.candidate_clients, declaration.client_count, document.population)
    if capabilities.population is not document.population:
        raise ScientificContractError(
            ErrorMessage("capability profile population mismatch"),
            subject=document.population,
            reason=PopulationIntegrityViolation.CAPABILITY_POPULATION_MISMATCH,
        )
    _validate_label_counts(membership, document.benign_row_count, document.attack_row_count)


def validate_split_manifest(
    membership: pl.DataFrame,
    assignments: pl.DataFrame,
    split_manifest: SplitManifestDocument,
) -> None:
    _require_columns(assignments, assignment_column_names(), StageOperationId.SPLIT)
    document = split_manifest
    _require_assignment_row_contract(assignments, membership, document.assignment_row_count, document.population)
    _require_role_counts(assignments, document)
    _require_benign_only_fit_roles(assignments, document.population)


def validate_no_future_history_leakage(
    assignments: pl.DataFrame,
    capture_timestamp_column: CaptureTimestampColumn,
) -> None:
    if capture_timestamp_column not in assignments.columns:
        raise ScientificContractError(
            ErrorMessage("chronological leakage check requires capture timestamps"),
            subject=StageOperationId.SPLIT,
            reason=PopulationIntegrityViolation.MISSING_CAPTURE_TIMESTAMPS,
        )
    historical = assignments.filter(
        pl.col(PARTITION_ROLE_COLUMN).is_in([PartitionRole.TRAIN, PartitionRole.CALIBRATION])
    )
    future = assignments.filter(
        pl.col(PARTITION_ROLE_COLUMN).is_in([PartitionRole.FUTURE_RECALIBRATION, PartitionRole.EVALUATION])
    )
    if historical.height == 0 or future.height == 0:
        return
    for client_id in assignments.get_column(CLIENT_ID_COLUMN).unique().sort().to_list():
        _reject_client_future_history_leakage(
            historical.filter(pl.col(CLIENT_ID_COLUMN) == client_id),
            future.filter(pl.col(CLIENT_ID_COLUMN) == client_id),
            capture_timestamp_column,
            ClientIdentityToken(client_id),
        )


def validate_dirichlet_conservation(
    membership: pl.DataFrame,
    source_row_count: RowCount,
    client_count: ClientCount,
) -> None:
    population = PopulationId.NBAIOT_DIRICHLET_CLIENTS
    if membership.height != source_row_count.value:
        raise DataIntegrityError(
            ErrorMessage("Dirichlet partition does not conserve source rows"),
            subject=population,
            reason=PopulationIntegrityViolation.DIRICHLET_SOURCE_ROWS_NOT_CONSERVED,
        )
    if membership.get_column(STABLE_ROW_ID_COLUMN).n_unique() != membership.height:
        raise DataIntegrityError(
            ErrorMessage("Dirichlet partition duplicated stable row identities"),
            subject=population,
            reason=PopulationIntegrityViolation.DIRICHLET_DUPLICATE_STABLE_ROW_IDENTITIES,
        )
    if membership.get_column(CLIENT_ID_COLUMN).n_unique() > client_count.value:
        raise DataIntegrityError(
            ErrorMessage("Dirichlet partition created more clients than declared"),
            subject=population,
            reason=PopulationIntegrityViolation.DIRICHLET_CLIENT_COUNT_EXCEEDED,
        )


def _require_membership_row_contract(
    membership: pl.DataFrame,
    expected_rows: RowCount,
    population: PopulationId,
) -> None:
    if membership.height != expected_rows.value:
        raise DataIntegrityError(
            ErrorMessage("membership row count disagrees with the population manifest"),
            subject=population,
            reason=PopulationIntegrityViolation.MEMBERSHIP_ROW_COUNT_MISMATCH,
        )
    if membership.get_column(STABLE_ROW_ID_COLUMN).n_unique() != membership.height:
        raise DataIntegrityError(
            ErrorMessage("membership contains duplicated stable row identities"),
            subject=population,
            reason=PopulationIntegrityViolation.MEMBERSHIP_DUPLICATE_STABLE_ROW_IDENTITIES,
        )


def _require_membership_client_subset(
    membership: pl.DataFrame,
    accepted_clients: tuple[ClientIdentityToken, ...],
    population: PopulationId,
) -> None:
    observed_clients = frozenset(membership.get_column(CLIENT_ID_COLUMN).unique().to_list())
    accepted = frozenset(c.value for c in accepted_clients)
    if not observed_clients <= accepted:
        raise DataIntegrityError(
            ErrorMessage("membership clients disagree with accepted client identities"),
            subject=population,
            reason=PopulationIntegrityViolation.MEMBERSHIP_CLIENTS_NOT_ACCEPTED,
        )
    if accepted_clients and not observed_clients and membership.height > 0:
        raise DataIntegrityError(
            ErrorMessage("membership is empty while the manifest records rows"),
            subject=population,
            reason=PopulationIntegrityViolation.MEMBERSHIP_EMPTY_WITH_NONZERO_MANIFEST,
        )


def _require_candidate_count(
    candidates: tuple[ClientIdentityToken, ...],
    expected: ClientCount,
    population: PopulationId,
) -> None:
    if len(candidates) != expected.value:
        raise DataIntegrityError(
            ErrorMessage("candidate client count disagrees with the population declaration"),
            subject=population,
            reason=PopulationIntegrityViolation.CANDIDATE_CLIENT_COUNT_MISMATCH,
        )


def _require_assignment_row_contract(
    assignments: pl.DataFrame,
    membership: pl.DataFrame,
    expected_rows: RowCount,
    population: PopulationId,
) -> None:
    if assignments.height != expected_rows.value:
        raise DataIntegrityError(
            ErrorMessage("assignment row count disagrees with the split manifest"),
            subject=population,
            reason=PopulationIntegrityViolation.ASSIGNMENT_ROW_COUNT_MISMATCH,
        )
    if assignments.height != membership.height:
        raise DataIntegrityError(
            ErrorMessage("split assignments do not conserve membership rows"),
            subject=population,
            reason=PopulationIntegrityViolation.ASSIGNMENT_ROWS_NOT_CONSERVED,
        )
    if assignments.get_column(STABLE_ROW_ID_COLUMN).n_unique() != assignments.height:
        raise DataIntegrityError(
            ErrorMessage("split assignments contain duplicated stable row identities"),
            subject=population,
            reason=PopulationIntegrityViolation.ASSIGNMENT_DUPLICATE_STABLE_ROW_IDENTITIES,
        )


def _require_role_counts(assignments: pl.DataFrame, document: SplitManifestDocument) -> None:
    for role, expected in (
        (PartitionRole.TRAIN, document.train_row_count),
        (PartitionRole.CALIBRATION, document.calibration_row_count),
        (PartitionRole.EVALUATION, document.evaluation_row_count),
        (PartitionRole.FUTURE_RECALIBRATION, document.future_recalibration_row_count),
        (PartitionRole.STATIC_REFERENCE_RESERVE, document.static_reference_reserve_row_count),
    ):
        observed = int(assignments.filter(pl.col(PARTITION_ROLE_COLUMN) == role).height)
        if observed != expected.value:
            raise DataIntegrityError(
                ErrorMessage(f"split role count mismatch for {role.value}"),
                subject=document.population,
                reason=PopulationIntegrityViolation.ROLE_COUNT_MISMATCH,
            )


def _require_benign_only_fit_roles(assignments: pl.DataFrame, population: PopulationId) -> None:
    train_calibration = assignments.filter(
        pl.col(PARTITION_ROLE_COLUMN).is_in([PartitionRole.TRAIN, PartitionRole.CALIBRATION])
    )
    if train_calibration.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            ErrorMessage("attack rows entered training or calibration"),
            subject=population,
            reason=PopulationIntegrityViolation.ATTACK_ROWS_IN_FIT_ROLES,
        )


def _reject_client_future_history_leakage(
    historical: pl.DataFrame,
    future: pl.DataFrame,
    capture_timestamp_column: CaptureTimestampColumn,
    client_id: ClientIdentityToken,
) -> None:
    if historical.height == 0 or future.height == 0:
        return
    boundary = historical.select(pl.col(capture_timestamp_column).max().alias(_MAX_HIST)).join(
        future.select(pl.col(capture_timestamp_column).min().alias(_MIN_FUT)),
        how="cross",
    )
    if boundary.filter(pl.col(_MAX_HIST) > pl.col(_MIN_FUT)).height > 0:
        raise LeakageError(
            ErrorMessage(f"future rows precede historical rows for client {client_id.value!r}"),
            subject=StageOperationId.SPLIT,
            reason=PopulationIntegrityViolation.FUTURE_PRECEDES_HISTORICAL,
        )


def _validate_label_counts(
    membership: pl.DataFrame,
    benign_count: RowCount,
    attack_count: RowCount,
) -> None:
    observed_benign, observed_attack = outcome_row_counts(membership)
    if observed_benign != benign_count or observed_attack != attack_count:
        raise DataIntegrityError(
            ErrorMessage("membership outcome counts disagree with the population manifest"),
            subject=PopulationFrameColumn.OUTCOME_LABEL,
            reason=PopulationIntegrityViolation.OUTCOME_COUNT_MISMATCH,
        )


def _require_columns(
    frame: pl.DataFrame,
    columns: tuple[ColumnName, ...],
    subject: StageOperationId,
) -> None:
    missing = tuple(column for column in columns if column not in frame.columns)
    if missing:
        raise DataIntegrityError(
            ErrorMessage(f"{subject.value} is missing required columns"),
            subject=subject,
            reason=PopulationIntegrityViolation.MISSING_REQUIRED_COLUMNS,
        )
