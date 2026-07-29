"""Exhaustive typed population catalogue dispatch."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.domain.enums import DatasetId, PartitionRole, PopulationId, SplitProtocolId
from datp_core.domain.errors import CapabilityError, ScientificContractError
from datp_core.domain.values import Seed
from datp_core.evaluation.cohorts import (
    ClientPartitionCounts,
    EvaluationCohortManifest,
    build_evaluation_cohort_manifest,
)
from datp_core.populations.capabilities import population_capabilities, population_declaration
from datp_core.populations.ciciot_file_clients import build_ciciot_file_clients
from datp_core.populations.edge_sensor_groups import build_edge_sensor_groups
from datp_core.populations.edge_temporal_groups import build_edge_temporal_groups
from datp_core.populations.models import (
    ChronologicalPartitionDiagnostics,
    CohortAggregationColumn,
    ControlledPartitionCondition,
    DirichletPartitionDiagnostics,
    PopulationCapabilities,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationOutcomeLabel,
    SplitConstructionRequest,
)
from datp_core.populations.nbaiot_dirichlet_clients import build_nbaiot_dirichlet_clients
from datp_core.populations.nbaiot_natural_devices import build_nbaiot_natural_devices
from datp_core.populations.splits import split_membership
from datp_core.protocols.models import PopulationDeclaration


@dataclass(frozen=True, slots=True)
class PopulationBinding:
    declaration: PopulationDeclaration
    capabilities: PopulationCapabilities


@dataclass(frozen=True, slots=True)
class PopulationConstructionResult:
    population: PopulationId
    manifest: PopulationManifest
    membership: pl.DataFrame
    diagnostics: DirichletPartitionDiagnostics | ChronologicalPartitionDiagnostics | None


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
    partition_seed: Seed
    split_protocol: SplitProtocolId
    dataset: DatasetId
    capture_timestamp_column: str | None = None


@dataclass(frozen=True, slots=True)
class PreprocessingHandoff:
    """Typed boundary from populations/splits/cohorts into Phase 04 preprocessing."""

    population_manifest: PopulationManifest
    membership: pl.DataFrame
    assignments: pl.DataFrame
    cohort_manifest: EvaluationCohortManifest


def resolve_population(population_id: PopulationId) -> PopulationBinding:
    match population_id:
        case (
            PopulationId.NBAIOT_NATURAL_DEVICES
            | PopulationId.CICIOT_FILE_CLIENTS
            | PopulationId.NBAIOT_DIRICHLET_CLIENTS
            | PopulationId.EDGE_SENSOR_GROUPS
            | PopulationId.EDGE_TEMPORAL_GROUPS
        ):
            return PopulationBinding(population_declaration(population_id), population_capabilities(population_id))
        case _:
            raise CapabilityError(
                "unsupported population identity",
                subject=population_id,
                reason="population is outside the locked five-population catalogue",
            )


def construct_population(request: PopulationConstructionRequest) -> PopulationConstructionResult:
    population_id = request.population_id
    canonical_root = request.canonical_root
    partition_seed = request.partition_seed
    split_protocol = request.split_protocol
    match population_id:
        case PopulationId.NBAIOT_NATURAL_DEVICES:
            if request.dirichlet_condition is not None:
                raise ScientificContractError(
                    "natural-device construction does not accept a synthetic partition condition",
                    subject=population_id,
                    reason="Dirichlet and IID conditions apply only to NBAIOT_DIRICHLET_CLIENTS",
                )
            manifest, membership = build_nbaiot_natural_devices(
                canonical_root, partition_seed=partition_seed, split_protocol=split_protocol
            )
            return PopulationConstructionResult(population_id, manifest, membership, None)
        case PopulationId.CICIOT_FILE_CLIENTS:
            if request.dirichlet_condition is not None:
                raise ScientificContractError(
                    "CIC file-client construction does not accept a synthetic partition condition",
                    subject=population_id,
                    reason="Dirichlet and IID conditions apply only to NBAIOT_DIRICHLET_CLIENTS",
                )
            manifest, membership = build_ciciot_file_clients(
                canonical_root, partition_seed=partition_seed, split_protocol=split_protocol
            )
            return PopulationConstructionResult(population_id, manifest, membership, None)
        case PopulationId.NBAIOT_DIRICHLET_CLIENTS:
            if request.dirichlet_condition is None:
                raise ScientificContractError(
                    "controlled N-BaIoT construction requires an explicit partition condition",
                    subject=population_id,
                    reason="Dirichlet concentration or IID must be declared, never defaulted",
                )
            manifest, membership, diagnostics = build_nbaiot_dirichlet_clients(
                canonical_root,
                partition_seed=partition_seed,
                condition=request.dirichlet_condition,
                split_protocol=split_protocol,
            )
            return PopulationConstructionResult(population_id, manifest, membership, diagnostics)
        case PopulationId.EDGE_SENSOR_GROUPS:
            if request.dirichlet_condition is not None:
                raise ScientificContractError(
                    "Edge sensor-group construction does not accept a synthetic partition condition",
                    subject=population_id,
                    reason="Dirichlet and IID conditions apply only to NBAIOT_DIRICHLET_CLIENTS",
                )
            manifest, membership = build_edge_sensor_groups(
                canonical_root, partition_seed=partition_seed, split_protocol=split_protocol
            )
            return PopulationConstructionResult(population_id, manifest, membership, None)
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            if request.dirichlet_condition is not None:
                raise ScientificContractError(
                    "Edge temporal construction does not accept a synthetic partition condition",
                    subject=population_id,
                    reason="Dirichlet and IID conditions apply only to NBAIOT_DIRICHLET_CLIENTS",
                )
            temporal_manifest, membership, diagnostics, _, _ = build_edge_temporal_groups(
                canonical_root, partition_seed=partition_seed, split_protocol=split_protocol
            )
            return PopulationConstructionResult(population_id, temporal_manifest, membership, diagnostics)
        case _:
            raise CapabilityError(
                "unsupported population identity",
                subject=population_id,
                reason="population is outside the locked five-population catalogue",
            )


def build_preprocessing_handoff(request: PreprocessingHandoffRequest) -> PreprocessingHandoff:
    construction = request.construction
    partition_seed = request.partition_seed
    split_protocol = request.split_protocol
    dataset = request.dataset
    capture_timestamp_column = request.capture_timestamp_column
    membership = construction.membership
    role_col = PopulationFrameColumn.PARTITION_ROLE
    if membership.height == 0:
        empty_assignments = membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(role_col))
        cohort = build_evaluation_cohort_manifest(
            population=construction.population,
            partition_seed=partition_seed,
            client_counts=tuple(
                ClientPartitionCounts(client_id, 0, 0, 0, False, False)
                for client_id in construction.manifest.document.candidate_clients
            ),
        )
        return PreprocessingHandoff(construction.manifest, membership, empty_assignments, cohort)

    assignments, _split_manifest = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=construction.population,
            dataset=dataset,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            population_manifest_checksum=construction.manifest.document.membership_checksum,
            capture_timestamp_column=capture_timestamp_column,
        )
    )
    counts = _client_partition_counts(assignments, construction.manifest.document.candidate_clients)
    cohort = build_evaluation_cohort_manifest(
        population=construction.population,
        partition_seed=partition_seed,
        client_counts=counts,
    )
    return PreprocessingHandoff(construction.manifest, membership, assignments, cohort)


def _client_partition_counts(
    assignments: pl.DataFrame, candidate_clients: tuple[str, ...]
) -> tuple[ClientPartitionCounts, ...]:
    client_col = PopulationFrameColumn.CLIENT_ID
    role_col = PopulationFrameColumn.PARTITION_ROLE
    outcome_col = PopulationFrameColumn.OUTCOME_LABEL
    cal_count = CohortAggregationColumn.BENIGN_CALIBRATION_COUNT
    eval_benign_count = CohortAggregationColumn.BENIGN_EVALUATION_COUNT
    attack_count = CohortAggregationColumn.ATTACK_EVALUATION_COUNT
    cal_benign = (pl.col(role_col) == PartitionRole.CALIBRATION) & (
        pl.col(outcome_col) == PopulationOutcomeLabel.BENIGN
    )
    eval_benign = (pl.col(role_col) == PartitionRole.EVALUATION) & (
        pl.col(outcome_col) == PopulationOutcomeLabel.BENIGN
    )
    eval_attack = (pl.col(role_col) == PartitionRole.EVALUATION) & (
        pl.col(outcome_col) == PopulationOutcomeLabel.ATTACK
    )
    summary = assignments.group_by(client_col).agg(
        pl.col(role_col).filter(cal_benign).len().alias(cal_count),
        pl.col(role_col).filter(eval_benign).len().alias(eval_benign_count),
        pl.col(role_col).filter(eval_attack).len().alias(attack_count),
    )
    candidates = pl.DataFrame({client_col.value: list(candidate_clients)})
    joined = candidates.join(summary, on=client_col.value, how="left").with_columns(
        pl.col(cal_count).fill_null(0),
        pl.col(eval_benign_count).fill_null(0),
        pl.col(attack_count).fill_null(0),
    )
    accepted = frozenset(assignments.get_column(client_col).unique().to_list())
    return tuple(
        ClientPartitionCounts(
            client_id=str(row[0]),
            benign_calibration_count=int(row[1]),
            benign_evaluation_count=int(row[2]),
            attack_evaluation_count=int(row[3]),
            accepted=str(row[0]) in accepted,
            deployment_fallback=False,
        )
        for row in joined.iter_rows()
    )
