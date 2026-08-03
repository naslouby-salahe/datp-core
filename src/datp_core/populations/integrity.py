"""Centralized population, split, and cohort integrity checks."""

from dataclasses import dataclass

import polars as pl

from datp_core.domain.enums import (
    DatasetId,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import DataIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, ClientCount, RowCount, Seed
from datp_core.populations.capabilities import population_capabilities, population_declaration
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationFeasibility,
    PopulationFeasibilityReason,
    PopulationFeasibilityStatus,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationManifestDocument,
    PopulationOutcomeLabel,
    SplitManifestDocument,
    WorkingFrameColumn,
    assignment_column_names,
    build_population_manifest,
    membership_checksum,
    membership_column_names,
    select_membership_frame,
)

_BENIGN = PopulationOutcomeLabel.BENIGN
_ATTACK = PopulationOutcomeLabel.ATTACK
_MAX_HIST = WorkingFrameColumn.MAX_HISTORICAL
_MIN_FUT = WorkingFrameColumn.MIN_FUTURE


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
) -> None:
    document = manifest.document
    declaration = population_declaration(document.population)
    capabilities = population_capabilities(document.population)
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


def validate_no_future_history_leakage(assignments: pl.DataFrame, capture_timestamp_column: str) -> None:
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
    if membership.height != source_row_count:
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


@dataclass(frozen=True, slots=True)
class FeasibilityAssessmentRequest:
    expected_count: ClientCount
    candidate_ids: tuple[str, ...]
    accepted_ids: tuple[str, ...]
    expected_identities: tuple[str, ...] | None
    chronology_required: bool


@dataclass(frozen=True, slots=True, eq=False)
class PopulationFinalizationRequest:
    population: PopulationId
    dataset: DatasetId
    identity_kind: PopulationIdentityKind
    partition_seed: Seed
    split_protocol: SplitProtocolId
    candidate_ids: tuple[str, ...]
    accepted_ids: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    expected_identities: tuple[str, ...] | None
    chronology_required: bool
    membership: pl.DataFrame
    canonical_schema_checksum: Checksum
    family_by_client: tuple[tuple[str, str], ...] = ()


def assess_declared_feasibility(
    *,
    expected_count: ClientCount,
    candidate_ids: tuple[str, ...],
    accepted_ids: tuple[str, ...],
    expected_identities: tuple[str, ...] | None,
    chronology_required: bool,
) -> PopulationFeasibility:
    """Shared feasibility gate used by every population builder."""
    return feasibility_from_candidates(
        FeasibilityAssessmentRequest(
            expected_count=expected_count,
            candidate_ids=candidate_ids,
            accepted_ids=accepted_ids,
            expected_identities=expected_identities,
            chronology_required=chronology_required,
        )
    )


def finalize_population(request: PopulationFinalizationRequest) -> PopulationManifest:
    """Build and validate a complete immutable population result from one typed request."""
    declaration = population_declaration(request.population)
    if declaration.dataset is not request.dataset or declaration.identity_kind is not request.identity_kind:
        raise ScientificContractError(
            "population finalization disagrees with its declaration",
            subject=request.population,
            reason="dataset and identity kind must come from the authoritative population binding",
        )
    membership = select_membership_frame(request.membership)
    benign, attack = outcome_row_counts(membership)
    feasibility = assess_declared_feasibility(
        expected_count=declaration.client_count,
        candidate_ids=request.candidate_ids,
        accepted_ids=request.accepted_ids,
        expected_identities=request.expected_identities,
        chronology_required=request.chronology_required,
    )
    manifest = build_population_manifest(
        PopulationManifestDocument(
            population=request.population,
            dataset=request.dataset,
            identity_kind=request.identity_kind,
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
            candidate_clients=request.candidate_ids,
            accepted_clients=request.accepted_ids,
            excluded_client_ids=request.excluded_ids,
            total_membership_rows=RowCount(membership.height),
            benign_row_count=benign,
            attack_row_count=attack,
            membership_checksum=membership_frame_checksum(membership),
            canonical_schema_checksum=request.canonical_schema_checksum,
            feasibility_status=feasibility.status,
            feasibility_reason=feasibility.reason,
        ),
        feasibility=feasibility,
        family_by_client=request.family_by_client,
    )
    validate_population_manifest(manifest, membership)
    return manifest


def feasibility_from_candidates(request: FeasibilityAssessmentRequest) -> PopulationFeasibility:
    expected = request.expected_count
    accepted_n = len(request.accepted_ids)
    identity_mismatch = request.expected_identities is not None and tuple(sorted(request.candidate_ids)) != tuple(
        sorted(request.expected_identities)
    )
    if identity_mismatch:
        return _infeasible(
            PopulationFeasibilityReason.IDENTITY_SET_MISMATCH,
            expected,
            accepted_n,
            "observed candidate identities disagree with the audited identity set",
        )
    if not request.chronology_required and len(request.candidate_ids) != request.expected_count:
        return _infeasible(
            PopulationFeasibilityReason.CANDIDATE_COUNT_MISMATCH,
            expected,
            accepted_n,
            "candidate client count disagrees with the population declaration",
        )
    if request.chronology_required and not request.accepted_ids:
        return _infeasible(
            PopulationFeasibilityReason.CHRONOLOGY_EVIDENCE_INSUFFICIENT,
            expected,
            0,
            "no groups remain after chronology eligibility validation",
        )
    if not request.accepted_ids:
        return _infeasible(
            PopulationFeasibilityReason.EMPTY_ACCEPTED_CLIENTS,
            expected,
            0,
            "population construction accepted no clients",
        )
    return PopulationFeasibility(
        PopulationFeasibilityStatus.FEASIBLE,
        PopulationFeasibilityReason.CANDIDATE_SET_MATCHES_DECLARATION,
        expected,
        ClientCount(accepted_n),
        "candidate and accepted client sets match the locked construction contract",
    )


def _infeasible(
    reason: PopulationFeasibilityReason,
    expected: ClientCount,
    observed: int,
    evidence: str,
) -> PopulationFeasibility:
    return PopulationFeasibility(
        PopulationFeasibilityStatus.INFEASIBLE, reason, expected, ClientCount(observed), evidence
    )


def _require_membership_row_contract(
    membership: pl.DataFrame, expected_rows: RowCount, population: PopulationId
) -> None:
    if membership.height != expected_rows:
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
    if len(candidates) != expected:
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
    if assignments.height != expected_rows:
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
        if observed != expected:
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
    capture_timestamp_column: str,
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
