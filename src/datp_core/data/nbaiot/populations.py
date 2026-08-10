"""N-BaIoT natural physical-device and controlled Dirichlet/IID population construction."""

from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.core.errors import (
    DataIntegrityError,
    ErrorMessage,
)
from datp_core.core.identifiers import (
    ClientIdentityToken,
    DatasetId,
    FamilyIdentity,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.core.numeric import CalibrationSize, ClientCount, RowCount, Seed
from datp_core.data.contracts import CanonicalProvenanceColumn
from datp_core.data.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.data.nbaiot.schema import (
    NBAIOT_DEVICE_IDENTITIES,
    NBaIoTCanonicalColumn,
    NBaIoTSourceLabel,
)
from datp_core.data.populations.construction import PopulationFinalizationRequest, finalize_population
from datp_core.data.populations.contracts import (
    CLIENT_ID_COLUMN,
    FAMILY_ID_COLUMN,
    NBAIOT_DIRICHLET_CLIENTS,
    NBAIOT_NATURAL_DEVICES,
    ORDER_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PERM_COLUMN,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    ControlledPartitionCondition,
    DirichletPartitionDiagnosticsDocument,
    FamilyAssignment,
    PopulationConstructionResult,
    PopulationFrameColumn,
    PopulationOutcomeLabel,
    build_population_capabilities,
    membership_column_names,
    population_evidence_role,
    select_membership_frame,
    synthetic_client_ids,
)
from datp_core.data.populations.controlled import ControlledPartitionAllocator
from datp_core.data.populations.integrity import validate_dirichlet_conservation
from datp_core.data.populations.paths import canonical_data_glob

_SOURCE_CLIENT = NBaIoTCanonicalColumn.PHYSICAL_CLIENT_ID
_SOURCE_FAMILY = NBaIoTCanonicalColumn.PHYSICAL_DEVICE_FAMILY
_SOURCE_LABEL = NBaIoTCanonicalColumn.RAW_LABEL
_NATURAL_POPULATION = PopulationId.NBAIOT_NATURAL_DEVICES
_NATURAL_IDENTITY = PopulationIdentityKind.PHYSICAL_DEVICES
_DIRICHLET_POPULATION = PopulationId.NBAIOT_DIRICHLET_CLIENTS
_DIRICHLET_IDENTITY = PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS


class NBaIoTPopulationViolation(StrEnum):
    UNEXPECTED_PHYSICAL_CLIENT_IDENTITIES = "unexpected_physical_client_identities"
    UNRECOGNIZED_OUTCOME_LABELS = "unrecognized_outcome_labels"
    STRATUM_ASSIGNMENT_LENGTH_MISMATCH = "stratum_assignment_length_mismatch"


def construct_nbaiot_natural_devices(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> PopulationConstructionResult:
    frame = _load_identity_frame(canonical_root)
    candidates = tuple(ClientIdentityToken(str(device)) for device in sorted(NBAIOT_DEVICE_IDENTITIES))
    observed = tuple(
        ClientIdentityToken(str(value)) for value in frame.get_column(CLIENT_ID_COLUMN).unique().sort().to_list()
    )
    if observed != candidates:
        raise DataIntegrityError(
            ErrorMessage("N-BaIoT physical-client identities disagree with the audited set"),
            subject=_NATURAL_POPULATION,
            reason=NBaIoTPopulationViolation.UNEXPECTED_PHYSICAL_CLIENT_IDENTITIES,
        )
    membership = select_membership_frame(frame).sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    family_by_client = tuple(
        FamilyAssignment(
            client=ClientIdentity(
                population=_NATURAL_POPULATION,
                client_id=ClientIdentityToken(str(client_id)),
                identity_kind=_NATURAL_IDENTITY,
            ),
            family=FamilyIdentity(str(family)),
        )
        for client_id, family in frame.select([CLIENT_ID_COLUMN, FAMILY_ID_COLUMN])
        .unique()
        .sort(CLIENT_ID_COLUMN)
        .iter_rows()
    )
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_NATURAL_POPULATION,
            dataset=DatasetId.NBAIOT,
            identity_kind=_NATURAL_IDENTITY,
            declaration=NBAIOT_NATURAL_DEVICES,
            capabilities=build_population_capabilities(
                NBAIOT_NATURAL_DEVICES,
                population_evidence_role(_NATURAL_POPULATION),
                NBAIOT_CAPABILITIES,
            ),
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=candidates,
            accepted_ids=candidates,
            excluded_ids=(),
            expected_identities=candidates,
            chronology_required=False,
            membership=membership,
            family_by_client=family_by_client,
        )
    )
    return PopulationConstructionResult(manifest, membership, None)


def construct_nbaiot_dirichlet_clients(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    condition: ControlledPartitionCondition,
    split_protocol: SplitProtocolId,
    minimum_benign_support: CalibrationSize,
) -> PopulationConstructionResult:
    source = _load_source_rows(canonical_root)
    client_ids = synthetic_client_ids(NBAIOT_DIRICHLET_CLIENTS.client_count)
    client_identities = client_ids
    allocator = ControlledPartitionAllocator(
        population=_DIRICHLET_POPULATION,
        client_count=NBAIOT_DIRICHLET_CLIENTS.client_count,
        condition=condition,
        seed=partition_seed,
    )
    membership, benign_counts, attack_counts = _partition_source(
        source,
        client_ids=client_identities,
        allocator=allocator,
    )
    validate_dirichlet_conservation(membership, RowCount(source.height), NBAIOT_DIRICHLET_CLIENTS.client_count)
    diagnostics = _build_diagnostics(
        client_ids=client_identities,
        client_count=NBAIOT_DIRICHLET_CLIENTS.client_count,
        membership_height=RowCount(source.height),
        benign_counts=benign_counts,
        attack_counts=attack_counts,
        condition=condition,
        partition_seed=partition_seed,
        minimum_benign_support=minimum_benign_support,
    )
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_DIRICHLET_POPULATION,
            dataset=DatasetId.NBAIOT,
            identity_kind=_DIRICHLET_IDENTITY,
            declaration=NBAIOT_DIRICHLET_CLIENTS,
            capabilities=build_population_capabilities(
                NBAIOT_DIRICHLET_CLIENTS,
                population_evidence_role(_DIRICHLET_POPULATION),
                NBAIOT_CAPABILITIES,
            ),
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=client_ids,
            accepted_ids=client_ids,
            excluded_ids=(),
            expected_identities=client_ids,
            chronology_required=False,
            membership=membership,
        )
    )
    return PopulationConstructionResult(manifest, membership, diagnostics)


def _load_identity_frame(canonical_root: Path) -> pl.DataFrame:
    frame = (
        pl.scan_parquet(canonical_data_glob(canonical_root))
        .select(
            pl.col(_SOURCE_CLIENT).alias(CLIENT_ID_COLUMN),
            pl.col(_SOURCE_FAMILY).alias(FAMILY_ID_COLUMN),
            pl.col(_SOURCE_LABEL),
            pl.col(CanonicalProvenanceColumn.STABLE_ROW_ID).alias(STABLE_ROW_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(PopulationFrameColumn.SOURCE_PATH),
            pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).alias(PopulationFrameColumn.SOURCE_ROW_INDEX),
        )
        .with_columns(
            pl.when(pl.col(_SOURCE_LABEL) == NBaIoTSourceLabel.BENIGN)
            .then(pl.lit(PopulationOutcomeLabel.BENIGN.value))
            .when(pl.col(_SOURCE_LABEL) == NBaIoTSourceLabel.ATTACK)
            .then(pl.lit(PopulationOutcomeLabel.ATTACK.value))
            .otherwise(pl.lit(None))
            .alias(OUTCOME_LABEL_COLUMN)
        )
        .collect(engine="streaming")
    )
    if frame.get_column(OUTCOME_LABEL_COLUMN).null_count() > 0:
        raise DataIntegrityError(
            ErrorMessage("N-BaIoT rows with unrecognized labels cannot enter the natural population"),
            subject=_NATURAL_POPULATION,
            reason=NBaIoTPopulationViolation.UNRECOGNIZED_OUTCOME_LABELS,
        )
    return frame


def _partition_source(
    source: pl.DataFrame,
    *,
    client_ids: tuple[ClientIdentityToken, ...],
    allocator: ControlledPartitionAllocator,
) -> tuple[pl.DataFrame, tuple[RowCount, ...], tuple[RowCount, ...]]:
    membership_parts: list[pl.DataFrame] = []
    benign_counts: list[RowCount] = [RowCount(0)] * allocator.client_count.value
    attack_counts: list[RowCount] = [RowCount(0)] * allocator.client_count.value
    for label, outcome in (
        (NBaIoTSourceLabel.BENIGN, PopulationOutcomeLabel.BENIGN),
        (NBaIoTSourceLabel.ATTACK, PopulationOutcomeLabel.ATTACK),
    ):
        stratum = source.filter(pl.col(_SOURCE_LABEL) == label).sort(STABLE_ROW_ID_COLUMN)
        stratum = _permute_stratum(stratum, allocator)
        counts = allocator.allocate(RowCount(stratum.height))
        membership_parts.append(
            _assign_stratum(
                stratum,
                client_ids,
                counts,
                outcome,
            )
        )
        target = benign_counts if outcome is PopulationOutcomeLabel.BENIGN else attack_counts
        for index, row_count in enumerate(counts):
            target[index] = target[index].plus(row_count)
    membership = pl.concat(membership_parts, how="vertical_relaxed").sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    return membership, tuple(benign_counts), tuple(attack_counts)


def _build_diagnostics(
    *,
    client_ids: tuple[ClientIdentityToken, ...],
    client_count: ClientCount,
    membership_height: RowCount,
    benign_counts: tuple[RowCount, ...],
    attack_counts: tuple[RowCount, ...],
    condition: ControlledPartitionCondition,
    partition_seed: Seed,
    minimum_benign_support: CalibrationSize,
) -> DirichletPartitionDiagnosticsDocument:
    client_row_counts = tuple(benign.plus(attack) for benign, attack in zip(benign_counts, attack_counts, strict=True))
    empty_ids = tuple(
        client_id for client_id, count in zip(client_ids, client_row_counts, strict=True) if count.value == 0
    )
    insufficient = tuple(
        client_id
        for client_id, benign in zip(client_ids, benign_counts, strict=True)
        if not minimum_benign_support.fits_within(benign)
    )
    return DirichletPartitionDiagnosticsDocument(
        population=_DIRICHLET_POPULATION,
        partition_seed=partition_seed,
        partition_kind=condition.kind,
        concentration=condition.concentration,
        client_count=client_count,
        client_ids=client_ids,
        total_rows=membership_height,
        client_row_counts=client_row_counts,
        benign_row_counts=benign_counts,
        attack_row_counts=attack_counts,
        empty_client_ids=empty_ids,
        insufficient_benign_client_ids=insufficient,
    )


def _permute_stratum(stratum: pl.DataFrame, allocator: ControlledPartitionAllocator) -> pl.DataFrame:
    row_count = RowCount(stratum.height)
    if row_count.value <= 1:
        return stratum
    return (
        stratum.with_row_index(ORDER_COLUMN)
        .with_columns(pl.Series(PERM_COLUMN, allocator.permutation(row_count)))
        .sort(PERM_COLUMN)
        .drop([ORDER_COLUMN, PERM_COLUMN])
    )


def _assign_stratum(
    stratum: pl.DataFrame,
    client_ids: tuple[ClientIdentityToken, ...],
    counts: tuple[RowCount, ...],
    outcome_label: PopulationOutcomeLabel,
) -> pl.DataFrame:
    if stratum.height == 0:
        return stratum.clear().with_columns(
            pl.lit(None, dtype=pl.String).alias(CLIENT_ID_COLUMN),
            pl.lit(outcome_label.value).alias(OUTCOME_LABEL_COLUMN),
        )
    client_column: list[str] = []
    for client_id, count in zip(client_ids, counts, strict=True):
        client_column.extend([client_id.value] * count.value)
    if len(client_column) != stratum.height:
        raise DataIntegrityError(
            ErrorMessage("stratum assignment length mismatch"),
            subject=_DIRICHLET_POPULATION,
            reason=NBaIoTPopulationViolation.STRATUM_ASSIGNMENT_LENGTH_MISMATCH,
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
