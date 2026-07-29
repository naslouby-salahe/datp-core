"""Controlled N-BaIoT Dirichlet and IID synthetic-client construction."""

from hashlib import sha256
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.datasets.models import CanonicalProvenanceColumn
from datp_core.datasets.nbaiot.schema import NBAIOT_SCHEMA, NBaIoTCanonicalColumn, NBaIoTSourceLabel
from datp_core.domain.enums import (
    ControlledPartitionKind,
    DatasetId,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.domain.errors import DataIntegrityError, ScientificContractError
from datp_core.domain.values import Checksum, ClientCount, Seed
from datp_core.populations.capabilities import population_declaration
from datp_core.populations.integrity import (
    assess_declared_feasibility,
    membership_frame_checksum,
    validate_dirichlet_conservation,
    validate_population_manifest,
)
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    ORDER_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PERM_COLUMN,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ControlledPartitionCondition,
    DirichletPartitionDiagnostics,
    DirichletPartitionDiagnosticsDocument,
    PopulationManifest,
    PopulationManifestSpec,
    PopulationOutcomeLabel,
    build_population_manifest,
    canonical_data_glob,
    hamilton_integer_counts,
    membership_column_names,
    synthetic_client_ids,
)
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT

_SOURCE_LABEL = NBaIoTCanonicalColumn.RAW_LABEL
_POPULATION = PopulationId.NBAIOT_DIRICHLET_CLIENTS
_IDENTITY = PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS


def build_nbaiot_dirichlet_clients(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    condition: ControlledPartitionCondition,
    split_protocol: SplitProtocolId,
) -> tuple[PopulationManifest, pl.DataFrame, DirichletPartitionDiagnostics]:
    declaration = population_declaration(_POPULATION)
    source = _load_source_rows(canonical_root)
    client_ids = synthetic_client_ids(declaration.client_count)
    membership, benign_counts, attack_counts = _partition_source(
        source,
        client_ids=client_ids,
        client_count=declaration.client_count.value,
        condition=condition,
        partition_seed=partition_seed,
    )
    validate_dirichlet_conservation(membership, source.height, declaration.client_count.value)
    diagnostics = _build_diagnostics(
        client_ids=client_ids,
        client_count=declaration.client_count,
        membership_height=membership.height,
        benign_counts=benign_counts,
        attack_counts=attack_counts,
        condition=condition,
        partition_seed=partition_seed,
    )
    feasibility = assess_declared_feasibility(
        expected_count=declaration.client_count.value,
        candidate_ids=client_ids,
        accepted_ids=client_ids,
        expected_identities=client_ids,
        chronology_required=False,
    )
    manifest = build_population_manifest(
        PopulationManifestSpec(
            population=_POPULATION,
            dataset=DatasetId.NBAIOT,
            identity_kind=_IDENTITY,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_clients=client_ids,
            accepted_clients=client_ids,
            excluded_client_ids=(),
            total_membership_rows=membership.height,
            benign_row_count=sum(benign_counts),
            attack_row_count=sum(attack_counts),
            membership_checksum=membership_frame_checksum(membership),
            canonical_schema_checksum=NBAIOT_SCHEMA.checksum,
            feasibility=feasibility,
        )
    )
    validate_population_manifest(manifest, membership)
    return manifest, membership, diagnostics


def _partition_source(
    source: pl.DataFrame,
    *,
    client_ids: tuple[str, ...],
    client_count: int,
    condition: ControlledPartitionCondition,
    partition_seed: Seed,
) -> tuple[pl.DataFrame, tuple[int, ...], tuple[int, ...]]:
    generator = np.random.Generator(np.random.PCG64(partition_seed.value))
    membership_parts: list[pl.DataFrame] = []
    benign_counts = [0] * client_count
    attack_counts = [0] * client_count
    for label, outcome in (
        (NBaIoTSourceLabel.BENIGN, PopulationOutcomeLabel.BENIGN),
        (NBaIoTSourceLabel.ATTACK, PopulationOutcomeLabel.ATTACK),
    ):
        stratum = source.filter(pl.col(_SOURCE_LABEL) == label).sort(STABLE_ROW_ID_COLUMN)
        stratum = _permute_stratum(stratum, generator)
        counts = _allocate_stratum(stratum.height, client_count, condition, generator)
        membership_parts.append(_assign_stratum(stratum, client_ids, counts, outcome))
        target = benign_counts if outcome is PopulationOutcomeLabel.BENIGN else attack_counts
        for index, count in enumerate(counts):
            target[index] += count
    membership = pl.concat(membership_parts, how="vertical_relaxed").sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    return membership, tuple(benign_counts), tuple(attack_counts)


def _build_diagnostics(
    *,
    client_ids: tuple[str, ...],
    client_count: ClientCount,
    membership_height: int,
    benign_counts: tuple[int, ...],
    attack_counts: tuple[int, ...],
    condition: ControlledPartitionCondition,
    partition_seed: Seed,
) -> DirichletPartitionDiagnostics:
    client_row_counts = tuple(benign + attack for benign, attack in zip(benign_counts, attack_counts, strict=True))
    empty_ids = tuple(client_id for client_id, count in zip(client_ids, client_row_counts, strict=True) if count == 0)
    insufficient = tuple(
        client_id
        for client_id, benign in zip(client_ids, benign_counts, strict=True)
        if benign < MINIMUM_BENIGN_SUPPORT.value
    )
    return DirichletPartitionDiagnostics(
        DirichletPartitionDiagnosticsDocument(
            population=_POPULATION,
            partition_seed=partition_seed,
            partition_kind=condition.kind,
            concentration=None if condition.concentration is None else condition.concentration.value,
            client_count=client_count,
            client_ids=client_ids,
            total_rows=membership_height,
            client_row_counts=client_row_counts,
            benign_row_counts=benign_counts,
            attack_row_counts=attack_counts,
            empty_client_ids=empty_ids,
            insufficient_benign_client_ids=insufficient,
            allocation_checksum=_allocation_checksum(client_ids, client_row_counts, condition, partition_seed),
        )
    )


def _allocate_stratum(
    row_count: int,
    client_count: int,
    condition: ControlledPartitionCondition,
    generator: np.random.Generator,
) -> tuple[int, ...]:
    if row_count == 0:
        return tuple(0 for _ in range(client_count))
    match condition.kind:
        case ControlledPartitionKind.IID:
            proportions = tuple(1.0 / client_count for _ in range(client_count))
        case ControlledPartitionKind.DIRICHLET:
            if condition.concentration is None:
                raise ScientificContractError(
                    "Dirichlet construction requires a concentration",
                    subject=_POPULATION,
                    reason="concentration cannot be invented",
                )
            alpha = np.full(client_count, condition.concentration.value, dtype=np.float64)
            proportions = tuple(float(value) for value in generator.dirichlet(alpha))
        case _:
            raise ScientificContractError(
                "unsupported controlled partition kind",
                subject=condition.kind,
                reason="only Dirichlet and IID constructions are authorized",
            )
    counts = hamilton_integer_counts(row_count, proportions)
    if sum(counts) != row_count:
        raise DataIntegrityError(
            "controlled partition allocation failed to conserve stratum rows",
            subject=_POPULATION,
            reason="Hamilton residual allocation must preserve every row",
        )
    return counts


def _permute_stratum(stratum: pl.DataFrame, generator: np.random.Generator) -> pl.DataFrame:
    if stratum.height <= 1:
        return stratum
    order = generator.permutation(stratum.height)
    return (
        stratum.with_row_index(ORDER_COLUMN)
        .with_columns(pl.Series(PERM_COLUMN, order))
        .sort(PERM_COLUMN)
        .drop([ORDER_COLUMN, PERM_COLUMN])
    )


def _assign_stratum(
    stratum: pl.DataFrame,
    client_ids: tuple[str, ...],
    counts: tuple[int, ...],
    outcome_label: PopulationOutcomeLabel,
) -> pl.DataFrame:
    if stratum.height == 0:
        return stratum.clear().with_columns(
            pl.lit(None, dtype=pl.String).alias(CLIENT_ID_COLUMN),
            pl.lit(outcome_label.value).alias(OUTCOME_LABEL_COLUMN),
        )
    client_column: list[str] = []
    for client_id, count in zip(client_ids, counts, strict=True):
        client_column.extend([client_id] * count)
    if len(client_column) != stratum.height:
        raise DataIntegrityError(
            "stratum assignment length mismatch",
            subject=_POPULATION,
            reason="allocation counts must cover the stratum exactly once",
        )
    return stratum.with_columns(
        pl.Series(CLIENT_ID_COLUMN, client_column),
        pl.lit(outcome_label.value).alias(OUTCOME_LABEL_COLUMN),
    ).select(membership_column_names())


def _load_source_rows(canonical_root: Path) -> pl.DataFrame:
    return (
        pl.scan_parquet(canonical_data_glob(canonical_root))
        .select(
            pl.col(_SOURCE_LABEL),
            pl.col(CanonicalProvenanceColumn.STABLE_ROW_ID).alias(STABLE_ROW_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).alias(SOURCE_ROW_INDEX_COLUMN),
        )
        .collect(engine="streaming")
    )


def _allocation_checksum(
    client_ids: tuple[str, ...],
    counts: tuple[int, ...],
    condition: ControlledPartitionCondition,
    partition_seed: Seed,
) -> Checksum:
    concentration = condition.kind.value if condition.concentration is None else str(condition.concentration.value)
    payload = "\n".join(
        (
            condition.kind.value,
            concentration,
            str(partition_seed.value),
            *client_ids,
            *(str(count) for count in counts),
        )
    )
    return Checksum(sha256(payload.encode()).hexdigest())
