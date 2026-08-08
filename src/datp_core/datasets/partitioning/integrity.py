"""Hard population, split, and cohort invariants.

Validators receive their declaration and capability context as explicit typed
inputs rather than resolving them from global registry state, so this module
stays independent of any specific dataset implementation or the registry.
"""

from collections.abc import Iterable

import polars as pl

from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PopulationId,
    StageOperationId,
)
from datp_core.domain.errors import DataIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import ClientCount, RowCount
from datp_core.domain.values.identifiers import CaptureTimestampColumn
from datp_core.data.populations.declarations import PopulationDeclaration

from .contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationCapabilities,
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


def reject_non_benign_labels(
    labels: Iterable[str],
    *,
    message: str,
    subject: ContractSubject,
    benign_label: str = PopulationOutcomeLabel.BENIGN.value,
) -> None:
    if any(label != benign_label for label in labels):
        raise LeakageError(message, subject=subject)


def membership_frame_checksum(membership: pl.DataFrame) -> Checksum:
    return membership_checksum(
        tuple(membership.get_column(CLIENT_ID_COLUMN).to_list()),
        tuple(membership.get_column(STABLE_ROW_ID_COLUMN).to_list()),
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
            "capability profile population mismatch",
            subject=document.population,
            reason="capabilities must be derived for the same population",
        )
    _validate_label_counts(membership, document.benign_row_count, document.attack_row_count)


def validate_split_manifest(
    membership: pl.DataFrame,
    assignments: pl.DataFrame,
    split_manifest: SplitManifestDocument,
) -> None:
    _require_columns(assignments, assignment_column_names(), StageOperationId.SPLIT)
    document = split_manifest
    population = document.population
    _require_assignment_row_contract(assignments, membership, document.assignment_row_count, population)
    _require_role_counts(assignments, document)
    _require_benign_only_fit_roles(assignments, population)


def validate_no_future_history_leakage(
    assignments: pl.DataFrame, capture_timestamp_column: CaptureTimestampColumn
) -> None:
    if capture_timestamp_column not in assignments.columns:
        raise ScientificContractError(
            "chronological leakage check requires capture timestamps",
            subject=StageOperationId.SPLIT,
            reason="temporal diagnostics cannot run without verified timestamps",
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
            str(client_id),
        )


def validate_dirichlet_conservation(
    membership: pl.DataFrame,
    source_row_count: RowCount,
    client_count: ClientCount,
) -> None:
    population = PopulationId.NBAIOT_DIRICHLET_CLIENTS
    if membership.height != source_row_count.value:
        raise DataIntegrityError(
            "Dirichlet partition does not conserve source rows",
            subject=population,
            reason="every eligible source row must appear exactly once",
        )
    if membership.get_column(STABLE_ROW_ID_COLUMN).n_unique() != membership.height:
        raise DataIntegrityError(
            "Dirichlet partition duplicated stable row identities",
            subject=population,
            reason="synthetic partitions must never duplicate rows",
        )
    if membership.get_column(CLIENT_ID_COLUMN).n_unique() > client_count.value:
        raise DataIntegrityError(
            "Dirichlet partition created more clients than declared",
            subject=population,
            reason="controlled partitions lock the client count at twenty",
        )


def _require_membership_row_contract(
    membership: pl.DataFrame, expected_rows: RowCount, population: PopulationId
) -> None:
    if membership.height != expected_rows.value:
        raise DataIntegrityError(
            "membership row count disagrees with the population manifest",
            subject=population,
            reason="manifests must match their membership frames",
        )
    if membership.get_column(STABLE_ROW_ID_COLUMN).n_unique() != membership.height:
        raise DataIntegrityError(
            "membership contains duplicated stable row identities",
            subject=population,
            reason="each source row may belong to at most one client",
        )


def _require_membership_client_subset(
    membership: pl.DataFrame,
    accepted_clients: tuple[str, ...],
    population: PopulationId,
) -> None:
    observed_clients = frozenset(membership.get_column(CLIENT_ID_COLUMN).unique().to_list())
    accepted = frozenset(accepted_clients)
    if not observed_clients <= accepted:
        raise DataIntegrityError(
            "membership clients disagree with accepted client identities",
            subject=population,
            reason="membership may only contain accepted clients; empty accepted clients may lack rows",
        )
    empty_with_rows = bool(accepted_clients) and not observed_clients and membership.height > 0
    if empty_with_rows:
        raise DataIntegrityError(
            "membership is empty while the manifest records rows",
            subject=population,
            reason="non-empty membership row counts require client identities",
        )


def _require_candidate_count(candidates: tuple[str, ...], expected: ClientCount, population: PopulationId) -> None:
    if len(candidates) != expected.value:
        raise DataIntegrityError(
            "candidate client count disagrees with the population declaration",
            subject=population,
            reason="candidate visibility must match the locked client count",
        )


def _require_assignment_row_contract(
    assignments: pl.DataFrame,
    membership: pl.DataFrame,
    expected_rows: RowCount,
    population: PopulationId,
) -> None:
    if assignments.height != expected_rows.value:
        raise DataIntegrityError(
            "assignment row count disagrees with the split manifest",
            subject=population,
            reason="split manifests must match their assignment frames",
        )
    if assignments.height != membership.height:
        raise DataIntegrityError(
            "split assignments do not conserve membership rows",
            subject=population,
            reason="every membership row requires exactly one split assignment",
        )
    if assignments.get_column(STABLE_ROW_ID_COLUMN).n_unique() != assignments.height:
        raise DataIntegrityError(
            "split assignments contain duplicated stable row identities",
            subject=population,
            reason="train, calibration, recalibration, and evaluation must be disjoint",
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
                f"split role count mismatch for {role.value}",
                subject=document.population,
                reason="manifest partition counts must match assignment rows",
            )


def _require_benign_only_fit_roles(assignments: pl.DataFrame, population: PopulationId) -> None:
    train_cal = assignments.filter(
        pl.col(PARTITION_ROLE_COLUMN).is_in([PartitionRole.TRAIN, PartitionRole.CALIBRATION])
    )
    if train_cal.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            "attack rows entered training or calibration",
            subject=population,
            reason="training and calibration are benign-only",
        )


def _reject_client_future_history_leakage(
    historical: pl.DataFrame,
    future: pl.DataFrame,
    capture_timestamp_column: CaptureTimestampColumn,
    client_id: str,
) -> None:
    if historical.height == 0 or future.height == 0:
        return
    boundary = historical.select(pl.col(capture_timestamp_column).max().alias(_MAX_HIST)).join(
        future.select(pl.col(capture_timestamp_column).min().alias(_MIN_FUT)),
        how="cross",
    )
    if boundary.filter(pl.col(_MAX_HIST) > pl.col(_MIN_FUT)).height > 0:
        raise LeakageError(
            f"future rows precede historical rows for client {client_id!r}",
            subject=StageOperationId.SPLIT,
            reason="chronological splits forbid future-to-history leakage",
        )


def _validate_label_counts(membership: pl.DataFrame, benign_count: RowCount, attack_count: RowCount) -> None:
    observed_benign, observed_attack = outcome_row_counts(membership)
    if observed_benign != benign_count or observed_attack != attack_count:
        raise DataIntegrityError(
            "membership outcome counts disagree with the population manifest",
            subject=PopulationFrameColumn.OUTCOME_LABEL,
            reason="benign and attack tallies must be exact",
        )


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...], subject: StageOperationId) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataIntegrityError(
            f"{subject.value} is missing required columns",
            subject=subject,
            reason="integrity validation requires the locked frame schema",
        )
