"""Edge-IIoTset chronology-verified temporal group population construction."""

from pathlib import Path

import polars as pl

from datp_core.datasets.edge_iiotset.capabilities import EDGE_TEMPORAL_SENSOR_GROUPS
from datp_core.datasets.edge_iiotset.schema import EDGE_SCHEMA, EdgeAssetRole, EdgeCanonicalColumn
from datp_core.datasets.models import (
    CanonicalManifestDocument,
    CanonicalProvenanceColumn,
    CanonicalPublicationArtifact,
    ChronologyDocument,
)
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.domain.errors import DataIntegrityError, ScientificContractError
from datp_core.domain.values import Checksum, RowCount, Seed
from datp_core.populations.capabilities import population_declaration
from datp_core.populations.integrity import (
    PopulationFinalizationRequest,
    finalize_population,
)
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ChronologicalPartitionDiagnostics,
    ChronologicalPartitionDiagnosticsDocument,
    PopulationManifest,
    PopulationOutcomeLabel,
    SplitConstructionRequest,
    SplitManifest,
    canonical_branch_directory,
    select_membership_frame,
)
from datp_core.populations.splits import split_membership

_GROUP = EdgeCanonicalColumn.BENIGN_SENSOR_GROUP
_CAPTURE = EdgeCanonicalColumn.CAPTURE_TIMESTAMP
_POPULATION = PopulationId.EDGE_TEMPORAL_GROUPS
_IDENTITY = PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS


def build_edge_temporal_groups(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> tuple[
    PopulationManifest,
    pl.DataFrame,
    ChronologicalPartitionDiagnostics,
    PopulationManifest,
    pl.DataFrame,
]:
    """Return temporal population plus matched random-fractional static reference over the same groups."""
    if split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise ScientificContractError(
            "Edge temporal groups require the locked chronological split protocol",
            subject=_POPULATION,
            reason="temporal populations cannot use non-temporal fractional splits as primary construction",
        )
    declaration = population_declaration(_POPULATION)
    eligible_ids, excluded_ids, exclusion_reasons, duplicate_timestamps = _chronology_eligibility(canonical_root)
    programme_candidates = tuple(group.value for group in sorted(EDGE_TEMPORAL_SENSOR_GROUPS))
    membership = _load_temporal_membership(canonical_root, eligible_ids) if eligible_ids else _empty_membership()
    diagnostics = ChronologicalPartitionDiagnostics(
        ChronologicalPartitionDiagnosticsDocument(
            population=_POPULATION,
            expected_group_count=declaration.client_count,
            observed_eligible_group_count=len(eligible_ids),
            eligible_group_ids=eligible_ids,
            excluded_group_ids=excluded_ids,
            exclusion_reasons=exclusion_reasons,
            duplicate_timestamp_rows=RowCount(duplicate_timestamps),
            total_temporal_rows=RowCount(membership.height),
        )
    )
    temporal_manifest = _assemble_manifest(
        partition_seed=partition_seed,
        split_protocol=split_protocol,
        programme_candidates=programme_candidates,
        accepted_ids=eligible_ids,
        excluded_ids=excluded_ids,
        membership=membership,
    )
    static_reference_manifest, static_reference_membership = _matched_static_reference(
        membership,
        partition_seed=partition_seed,
        eligible_ids=eligible_ids,
        programme_candidates=programme_candidates,
    )
    return temporal_manifest, membership, diagnostics, static_reference_manifest, static_reference_membership


def _assemble_manifest(
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
    programme_candidates: tuple[str, ...],
    accepted_ids: tuple[str, ...],
    excluded_ids: tuple[str, ...],
    membership: pl.DataFrame,
) -> PopulationManifest:
    selected = select_membership_frame(membership)
    return finalize_population(
        PopulationFinalizationRequest(
            population=_POPULATION,
            dataset=DatasetId.EDGE_IIOTSET,
            identity_kind=_IDENTITY,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=programme_candidates,
            accepted_ids=accepted_ids,
            excluded_ids=excluded_ids,
            expected_identities=programme_candidates,
            chronology_required=True,
            membership=selected,
            canonical_schema_checksum=EDGE_SCHEMA.checksum,
        )
    )


def _chronology_eligibility(
    canonical_root: Path,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], int]:
    manifest_path = Path(canonical_root) / CanonicalPublicationArtifact.MANIFEST
    if not manifest_path.is_file():
        raise DataIntegrityError(
            "Edge canonical manifest is required for temporal eligibility",
            subject=_POPULATION,
            reason="chronology must be read from persisted evidence",
        )
    document = CanonicalManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    eligible: list[str] = []
    excluded: list[str] = []
    reasons: list[str] = []
    duplicate_total = 0
    for group in sorted(EDGE_TEMPORAL_SENSOR_GROUPS):
        group_id = group.value
        evidence = _chronology_for_group(group_id, document.chronology)
        if evidence is None:
            excluded.append(group_id)
            reasons.append("chronology evidence absent from the canonical manifest")
            continue
        duplicate_total += evidence.duplicate_timestamp_count
        if evidence.temporal_eligible:
            eligible.append(group_id)
        else:
            excluded.append(group_id)
            reasons.append(evidence.reason)
    return tuple(eligible), tuple(excluded), tuple(reasons), duplicate_total


def _chronology_for_group(group_id: str, chronology: tuple[ChronologyDocument, ...]) -> ChronologyDocument | None:
    for item in chronology:
        if item.group_identity == group_id:
            return item
    return None


def _load_temporal_membership(canonical_root: Path, eligible_ids: tuple[str, ...]) -> pl.DataFrame:
    temporal_root = canonical_branch_directory(canonical_root, EdgeAssetRole.TEMPORAL_BENIGN)
    paths = tuple(temporal_root / f"{group_id}.parquet" for group_id in eligible_ids)
    missing = tuple(path.name for path in paths if not path.is_file())
    if missing:
        raise DataIntegrityError(
            "temporal assets are missing for chronology-eligible groups",
            subject=_POPULATION,
            reason="eligible temporal groups require published temporal_benign parquet assets",
        )
    frame = (
        pl.scan_parquet([str(path) for path in paths])
        .select(
            pl.col(_GROUP).alias(CLIENT_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.STABLE_ROW_ID).alias(STABLE_ROW_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).alias(SOURCE_ROW_INDEX_COLUMN),
            pl.col(_CAPTURE),
            pl.lit(PopulationOutcomeLabel.BENIGN.value).alias(OUTCOME_LABEL_COLUMN),
        )
        .collect(engine="streaming")
        .sort([CLIENT_ID_COLUMN, _CAPTURE, SOURCE_ROW_INDEX_COLUMN, STABLE_ROW_ID_COLUMN])
    )
    if frame.get_column(_CAPTURE).null_count() > 0:
        raise ScientificContractError(
            "temporal membership contains null capture timestamps",
            subject=_POPULATION,
            reason="chronology-eligible assets must retain verified capture timestamps",
        )
    return frame


def _empty_membership() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            CLIENT_ID_COLUMN.value: pl.String,
            STABLE_ROW_ID_COLUMN.value: pl.String,
            SOURCE_PATH_COLUMN.value: pl.String,
            SOURCE_ROW_INDEX_COLUMN.value: pl.UInt64,
            _CAPTURE.value: pl.Datetime(time_unit="ns", time_zone="UTC"),
            OUTCOME_LABEL_COLUMN.value: pl.String,
        }
    )


def _matched_static_reference(
    temporal_membership: pl.DataFrame,
    *,
    partition_seed: Seed,
    eligible_ids: tuple[str, ...],
    programme_candidates: tuple[str, ...],
) -> tuple[PopulationManifest, pl.DataFrame]:
    membership = select_membership_frame(temporal_membership)
    accepted = frozenset(eligible_ids)
    excluded = tuple(client for client in programme_candidates if client not in accepted)
    manifest = _assemble_manifest(
        partition_seed=partition_seed,
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        programme_candidates=programme_candidates,
        accepted_ids=eligible_ids,
        excluded_ids=excluded,
        membership=membership,
    )
    return manifest, membership


def split_temporal_membership(
    membership: pl.DataFrame,
    *,
    partition_seed: Seed,
    population_manifest_checksum: Checksum,
) -> tuple[pl.DataFrame, SplitManifest]:
    return split_membership(
        SplitConstructionRequest(
            membership=membership.select(
                CLIENT_ID_COLUMN,
                STABLE_ROW_ID_COLUMN,
                OUTCOME_LABEL_COLUMN,
                SOURCE_PATH_COLUMN,
                SOURCE_ROW_INDEX_COLUMN,
                _CAPTURE,
            ),
            population=_POPULATION,
            dataset=DatasetId.EDGE_IIOTSET,
            partition_seed=partition_seed,
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            population_manifest_checksum=population_manifest_checksum,
            capture_timestamp_column=_CAPTURE.value,
        )
    )
