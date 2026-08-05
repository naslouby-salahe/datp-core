"""Exhaustive typed population catalogue dispatch."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.domain.enums import (
    ContractSubject,
    ControlledPartitionKind,
    EvidenceRole,
    PartitionRole,
    PopulationId,
    SplitProtocolId,
)
from datp_core.domain.errors import CapabilityError, ScientificContractError
from datp_core.domain.values import FeatureNameSequence, RowCount, Seed
from datp_core.populations.capabilities import (
    population_capabilities,
    population_evidence_role,
)
from datp_core.populations.ciciot_file_clients import build_ciciot_file_clients
from datp_core.populations.edge_sensor_groups import build_edge_sensor_groups
from datp_core.populations.edge_temporal_groups import build_edge_temporal_groups
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ChronologicalPartitionDiagnosticsDocument,
    ClientIdentity,
    ClientPartitionCounts,
    CohortAggregationColumn,
    ControlledPartitionCondition,
    DirichletPartitionDiagnosticsDocument,
    PopulationCapabilities,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationOutcomeLabel,
    SplitConstructionRequest,
    canonical_data_glob,
)
from datp_core.populations.nbaiot_dirichlet_clients import (
    build_nbaiot_dirichlet_clients,
)
from datp_core.populations.nbaiot_natural_devices import (
    build_nbaiot_natural_devices,
)
from datp_core.populations.splits import split_membership
from datp_core.protocols.models import PopulationDeclaration
from datp_core.protocols.populations import (
    CICIOT_FILE_CLIENTS,
    EDGE_SENSOR_GROUPS,
    EDGE_TEMPORAL_GROUPS,
    NBAIOT_DIRICHLET_CLIENTS,
    NBAIOT_NATURAL_DEVICES,
)


@dataclass(frozen=True, slots=True)
class PopulationBinding:
    population: PopulationId
    declaration: PopulationDeclaration
    evidentiary_role: EvidenceRole
    capabilities: PopulationCapabilities
    supported_partition_kinds: frozenset[ControlledPartitionKind]
    construct: Callable[["PopulationConstructionRequest"], "PopulationConstructionResult"]


@dataclass(slots=True, eq=False)
class PopulationConstructionResult:
    manifest: PopulationManifest
    membership: pl.DataFrame
    diagnostics: DirichletPartitionDiagnosticsDocument | ChronologicalPartitionDiagnosticsDocument | None

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
    capture_timestamp_column: str | None = None


@dataclass(slots=True, eq=False)
class PreprocessingHandoff:
    """Typed boundary from populations/splits into preprocessing."""

    population_manifest: PopulationManifest
    membership: pl.DataFrame
    assignments: pl.DataFrame
    client_partition_counts: tuple[ClientPartitionCounts, ...]
    deployment_fallback_client_ids: frozenset[ClientIdentity] = frozenset()


def resolve_population(population_id: PopulationId) -> PopulationBinding:
    matches = tuple(binding for binding in _POPULATION_BINDINGS if binding.population is population_id)
    if len(matches) != 1:
        raise CapabilityError(
            "unsupported population identity",
            subject=population_id,
            reason="population is outside the locked five-population catalogue",
        )
    return matches[0]


def construct_population(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    binding = resolve_population(request.population_id)
    _require_partition_condition(request, binding)
    return binding.construct(request)


def _require_partition_condition(
    request: PopulationConstructionRequest,
    binding: PopulationBinding,
) -> None:
    condition = request.dirichlet_condition
    if not binding.supported_partition_kinds:
        if condition is not None:
            raise ScientificContractError(
                "population construction does not accept a controlled partition condition",
                subject=request.population_id,
                reason=("only populations with declared controlled partition capability accept one"),
            )
        return
    if condition is None:
        raise ScientificContractError(
            "controlled population construction requires an explicit partition condition",
            subject=request.population_id,
            reason="a controlled partition is never defaulted",
        )
    if condition.kind not in binding.supported_partition_kinds:
        raise ScientificContractError(
            "population construction received an unsupported controlled partition kind",
            subject=request.population_id,
            reason="the partition kind is absent from the population binding",
        )


def _construct_nbaiot_natural(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    manifest, membership = build_nbaiot_natural_devices(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )
    return PopulationConstructionResult(manifest, membership, None)


def _construct_ciciot_file_clients(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    manifest, membership = build_ciciot_file_clients(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )
    return PopulationConstructionResult(manifest, membership, None)


def _construct_nbaiot_dirichlet(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    condition = request.dirichlet_condition
    if condition is None:
        raise AssertionError("partition condition was validated before binding dispatch")
    manifest, membership, diagnostics = build_nbaiot_dirichlet_clients(
        request.canonical_root,
        partition_seed=request.partition_seed,
        condition=condition,
        split_protocol=request.split_protocol,
    )
    return PopulationConstructionResult(manifest, membership, diagnostics)


def _construct_edge_sensor_groups(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    manifest, membership = build_edge_sensor_groups(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )
    return PopulationConstructionResult(manifest, membership, None)


def _construct_edge_temporal_groups(
    request: PopulationConstructionRequest,
) -> PopulationConstructionResult:
    manifest, membership, diagnostics, _, _ = build_edge_temporal_groups(
        request.canonical_root,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
    )
    return PopulationConstructionResult(manifest, membership, diagnostics)


_POPULATION_BINDINGS = (
    PopulationBinding(
        PopulationId.NBAIOT_NATURAL_DEVICES,
        NBAIOT_NATURAL_DEVICES,
        population_evidence_role(PopulationId.NBAIOT_NATURAL_DEVICES),
        population_capabilities(PopulationId.NBAIOT_NATURAL_DEVICES),
        frozenset(),
        _construct_nbaiot_natural,
    ),
    PopulationBinding(
        PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        NBAIOT_DIRICHLET_CLIENTS,
        population_evidence_role(PopulationId.NBAIOT_DIRICHLET_CLIENTS),
        population_capabilities(PopulationId.NBAIOT_DIRICHLET_CLIENTS),
        frozenset(ControlledPartitionKind),
        _construct_nbaiot_dirichlet,
    ),
    PopulationBinding(
        PopulationId.CICIOT_FILE_CLIENTS,
        CICIOT_FILE_CLIENTS,
        population_evidence_role(PopulationId.CICIOT_FILE_CLIENTS),
        population_capabilities(PopulationId.CICIOT_FILE_CLIENTS),
        frozenset(),
        _construct_ciciot_file_clients,
    ),
    PopulationBinding(
        PopulationId.EDGE_SENSOR_GROUPS,
        EDGE_SENSOR_GROUPS,
        population_evidence_role(PopulationId.EDGE_SENSOR_GROUPS),
        population_capabilities(PopulationId.EDGE_SENSOR_GROUPS),
        frozenset(),
        _construct_edge_sensor_groups,
    ),
    PopulationBinding(
        PopulationId.EDGE_TEMPORAL_GROUPS,
        EDGE_TEMPORAL_GROUPS,
        population_evidence_role(PopulationId.EDGE_TEMPORAL_GROUPS),
        population_capabilities(PopulationId.EDGE_TEMPORAL_GROUPS),
        frozenset(),
        _construct_edge_temporal_groups,
    ),
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
