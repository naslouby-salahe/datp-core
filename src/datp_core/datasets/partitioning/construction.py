"""Dataset-independent population feasibility, finalization, and handoff construction."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    ClientCount,
    FeatureNameSequence,
    NonNegativeIntegerValue,
    RowCount,
    Seed,
)
from datp_core.protocols.models import PopulationDeclaration

from .contracts import (
    CLIENT_ID_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    ClientPartitionCounts,
    CohortAggregationColumn,
    PopulationCapabilities,
    PopulationFeasibility,
    PopulationFeasibilityReason,
    PopulationFeasibilityStatus,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationManifestDocument,
    PopulationOutcomeLabel,
    PreprocessingHandoff,
    PreprocessingHandoffRequest,
    SplitConstructionRequest,
    build_population_manifest,
    canonical_data_glob,
    select_membership_frame,
)
from .integrity import membership_frame_checksum, outcome_row_counts, validate_population_manifest
from .splits import split_membership


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
    declaration: PopulationDeclaration
    capabilities: PopulationCapabilities
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
    declaration = request.declaration
    if (
        declaration.id is not request.population
        or declaration.dataset is not request.dataset
        or declaration.identity_kind is not request.identity_kind
    ):
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
    validate_population_manifest(manifest, membership, declaration, request.capabilities)
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
        NonNegativeIntegerValue(accepted_n),
        "candidate and accepted client sets match the locked construction contract",
    )


def build_preprocessing_handoff(
    request: PreprocessingHandoffRequest,
) -> PreprocessingHandoff:
    construction = request.construction
    document = construction.manifest.document
    membership = construction.membership
    candidate_clients = construction.manifest.clients
    fallback_clients = _deployment_fallback_clients(
        candidate_clients,
        request.deployment_fallback_client_ids,
    )
    role_column = PopulationFrameColumn.PARTITION_ROLE
    if membership.height == 0:
        assignments = membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(role_column))
        counts = tuple(
            ClientPartitionCounts(
                client=client,
                benign_calibration_count=RowCount(0),
                benign_evaluation_count=RowCount(0),
                attack_evaluation_count=RowCount(0),
                accepted=False,
                deployment_fallback=client in fallback_clients,
            )
            for client in candidate_clients
        )
        return PreprocessingHandoff(
            population_manifest=construction.manifest,
            membership=membership,
            assignments=assignments,
            client_partition_counts=counts,
            deployment_fallback_client_ids=fallback_clients,
        )
    assignments, _ = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=document.population,
            dataset=document.dataset,
            partition_seed=document.partition_seed,
            split_protocol=document.split_protocol,
            population_manifest_checksum=document.membership_checksum,
            capture_timestamp_column=request.capture_timestamp_column,
        )
    )
    return PreprocessingHandoff(
        population_manifest=construction.manifest,
        membership=membership,
        assignments=assignments,
        client_partition_counts=_client_partition_counts(
            assignments,
            candidate_clients,
            deployment_fallback_clients=fallback_clients,
        ),
        deployment_fallback_client_ids=fallback_clients,
    )


def join_handoff_with_canonical_features(
    canonical_root: Path,
    handoff: PreprocessingHandoff,
    feature_names: FeatureNameSequence,
) -> pl.DataFrame:
    assignments = handoff.assignments
    if assignments.height == 0:
        raise ScientificContractError(
            "preprocessing handoff produced empty split assignments",
            subject=handoff.population_manifest.document.population,
        )
    feature_scan = pl.scan_parquet(canonical_data_glob(canonical_root)).select([STABLE_ROW_ID_COLUMN, *feature_names])
    joined = (
        assignments.lazy()
        .join(feature_scan, on=STABLE_ROW_ID_COLUMN, how="inner")
        .collect()
        .sort(
            [
                CLIENT_ID_COLUMN,
                PARTITION_ROLE_COLUMN,
                STABLE_ROW_ID_COLUMN,
            ]
        )
    )
    if joined.height != assignments.height:
        raise ScientificContractError(
            "canonical feature join lost assignment rows",
            subject=handoff.population_manifest.document.dataset,
        )
    return joined


def _infeasible(
    reason: PopulationFeasibilityReason,
    expected: ClientCount,
    observed: int,
    evidence: str,
) -> PopulationFeasibility:
    return PopulationFeasibility(
        PopulationFeasibilityStatus.INFEASIBLE, reason, expected, NonNegativeIntegerValue(observed), evidence
    )


def _deployment_fallback_clients(
    candidate_clients: tuple[ClientIdentity, ...],
    fallback_client_ids: frozenset[str],
) -> frozenset[ClientIdentity]:
    matches = frozenset(client for client in candidate_clients if client.client_id in fallback_client_ids)
    if frozenset(client.client_id for client in matches) != fallback_client_ids:
        raise ScientificContractError(
            "deployment-fallback client ids must be subset of population candidate clients",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches


def _client_partition_counts(
    assignments: pl.DataFrame,
    candidate_clients: tuple[ClientIdentity, ...],
    *,
    deployment_fallback_clients: frozenset[ClientIdentity],
) -> tuple[ClientPartitionCounts, ...]:
    client_column = PopulationFrameColumn.CLIENT_ID
    role_column = PopulationFrameColumn.PARTITION_ROLE
    outcome_column = PopulationFrameColumn.OUTCOME_LABEL
    calibration_count = CohortAggregationColumn.BENIGN_CALIBRATION_COUNT
    benign_evaluation_count = CohortAggregationColumn.BENIGN_EVALUATION_COUNT
    attack_evaluation_count = CohortAggregationColumn.ATTACK_EVALUATION_COUNT
    summary = assignments.group_by(client_column).agg(
        pl.col(role_column)
        .filter(
            (pl.col(role_column) == PartitionRole.CALIBRATION)
            & (pl.col(outcome_column) == PopulationOutcomeLabel.BENIGN)
        )
        .len()
        .alias(calibration_count),
        pl.col(role_column)
        .filter(
            (pl.col(role_column) == PartitionRole.EVALUATION)
            & (pl.col(outcome_column) == PopulationOutcomeLabel.BENIGN)
        )
        .len()
        .alias(benign_evaluation_count),
        pl.col(role_column)
        .filter(
            (pl.col(role_column) == PartitionRole.EVALUATION)
            & (pl.col(outcome_column) == PopulationOutcomeLabel.ATTACK)
        )
        .len()
        .alias(attack_evaluation_count),
    )
    joined = (
        pl.DataFrame(
            (
                pl.Series(
                    client_column.value,
                    tuple(client.client_id for client in candidate_clients),
                    dtype=pl.String,
                ),
            )
        )
        .join(summary, on=client_column.value, how="left")
        .with_columns(
            pl.col(calibration_count).fill_null(0),
            pl.col(benign_evaluation_count).fill_null(0),
            pl.col(attack_evaluation_count).fill_null(0),
        )
    )
    accepted = frozenset(str(value) for value in assignments.get_column(client_column).unique().to_list())
    return tuple(
        ClientPartitionCounts(
            client=(client := _client_identity(candidate_clients, str(row[0]))),
            benign_calibration_count=RowCount(int(row[1])),
            benign_evaluation_count=RowCount(int(row[2])),
            attack_evaluation_count=RowCount(int(row[3])),
            accepted=str(row[0]) in accepted,
            deployment_fallback=client in deployment_fallback_clients,
        )
        for row in joined.iter_rows()
    )


def _client_identity(
    clients: tuple[ClientIdentity, ...],
    client_id: str,
) -> ClientIdentity:
    matches = tuple(client for client in clients if client.client_id == client_id)
    if len(matches) != 1:
        raise ScientificContractError(
            "population manifest client identity lookup failed",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]
