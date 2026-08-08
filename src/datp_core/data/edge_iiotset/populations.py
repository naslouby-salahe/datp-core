"""Edge-IIoTset static sensor-group and chronology-verified temporal-group population construction."""

from pathlib import Path

import polars as pl

from datp_core.data.contracts import (
    CanonicalManifestDocument,
    CanonicalProvenanceColumn,
    CanonicalPublicationArtifact,
)
from datp_core.data.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES, EDGE_TEMPORAL_SENSOR_GROUPS
from datp_core.data.edge_iiotset.schema import (
    EDGE_BENIGN_SENSOR_GROUPS,
    EDGE_SCHEMA,
    EdgeAssetRole,
    EdgeCanonicalColumn,
    EdgeSensorGroup,
)
from datp_core.data.populations.construction import PopulationFinalizationRequest, finalize_population
from datp_core.data.populations.contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ChronologicalPartitionDiagnosticsDocument,
    ChronologyExclusionReason,
    MatchedReferencePopulation,
    PopulationConstructionResult,
    PopulationManifest,
    PopulationOutcomeLabel,
    build_population_capabilities,
    population_evidence_role,
    select_membership_frame,
)
from datp_core.data.populations.paths import PartitioningFilePattern, canonical_branch_directory
from datp_core.core.errors import CapabilityError, DataIntegrityError, ScientificContractError
from datp_core.core.identifiers import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.core.numeric import NonNegativeIntegerValue, RowCount, Seed
from datp_core.data.populations.declarations import EDGE_SENSOR_GROUPS, EDGE_TEMPORAL_GROUPS

_GROUP = EdgeCanonicalColumn.BENIGN_SENSOR_GROUP
_CAPTURE = EdgeCanonicalColumn.CAPTURE_TIMESTAMP
_SENSOR_POPULATION = PopulationId.EDGE_SENSOR_GROUPS
_SENSOR_IDENTITY = PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS
_TEMPORAL_POPULATION = PopulationId.EDGE_TEMPORAL_GROUPS
_TEMPORAL_IDENTITY = PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS


def construct_edge_sensor_groups(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> PopulationConstructionResult:
    if split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise CapabilityError(
            "static Edge sensor groups do not use chronological splits",
            subject=_SENSOR_POPULATION,
            reason="temporal analysis uses EDGE_TEMPORAL_GROUPS exclusively",
        )
    candidates = tuple(group.value for group in EDGE_BENIGN_SENSOR_GROUPS)
    membership = _load_static_membership(canonical_root)
    observed = tuple(membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    expected = tuple(sorted(candidates))
    if observed != expected:
        raise DataIntegrityError(
            "Edge static sensor-group identities disagree with the audited set",
            subject=_SENSOR_POPULATION,
            reason="static construction requires exactly the ten audited benign folders",
        )
    if membership.filter(pl.col(OUTCOME_LABEL_COLUMN) != PopulationOutcomeLabel.BENIGN).height > 0:
        raise DataIntegrityError(
            "Edge static sensor groups cannot carry attack rows",
            subject=_SENSOR_POPULATION,
            reason="attack traffic remains unassigned to sensor identities",
        )
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_SENSOR_POPULATION,
            dataset=DatasetId.EDGE_IIOTSET,
            identity_kind=_SENSOR_IDENTITY,
            declaration=EDGE_SENSOR_GROUPS,
            capabilities=build_population_capabilities(
                EDGE_SENSOR_GROUPS,
                population_evidence_role(_SENSOR_POPULATION),
                EDGE_IIOTSET_CAPABILITIES,
            ),
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=expected,
            accepted_ids=expected,
            excluded_ids=(),
            expected_identities=expected,
            chronology_required=False,
            membership=select_membership_frame(membership),
            canonical_schema_checksum=EDGE_SCHEMA.checksum,
        )
    )
    return PopulationConstructionResult(manifest, membership, None)


def construct_edge_temporal_groups(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> PopulationConstructionResult:
    """Return the temporal population plus its matched random-fractional static reference."""
    if split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise ScientificContractError(
            "Edge temporal groups require the locked chronological split protocol",
            subject=_TEMPORAL_POPULATION,
            reason="temporal populations cannot use non-temporal fractional splits as primary construction",
        )
    eligible_ids, excluded_ids, exclusion_reasons, duplicate_timestamps = _chronology_eligibility(canonical_root)
    programme_candidates = tuple(group.value for group in sorted(EDGE_TEMPORAL_SENSOR_GROUPS))
    membership = _load_temporal_membership(canonical_root, eligible_ids) if eligible_ids else _empty_membership()
    diagnostics = ChronologicalPartitionDiagnosticsDocument(
        population=_TEMPORAL_POPULATION,
        expected_group_count=EDGE_TEMPORAL_GROUPS.client_count,
        observed_eligible_group_count=NonNegativeIntegerValue(len(eligible_ids)),
        eligible_group_ids=eligible_ids,
        excluded_group_ids=excluded_ids,
        exclusion_reasons=exclusion_reasons,
        duplicate_timestamp_rows=RowCount(duplicate_timestamps),
        total_temporal_rows=RowCount(membership.height),
    )
    temporal_manifest = _finalize_temporal_manifest(
        partition_seed=partition_seed,
        split_protocol=split_protocol,
        programme_candidates=programme_candidates,
        accepted_ids=eligible_ids,
        excluded_ids=tuple(group_id for group_id in excluded_ids if group_id in programme_candidates),
        membership=membership,
    )
    static_reference_manifest, static_reference_membership = _matched_static_reference(
        membership,
        partition_seed=partition_seed,
        eligible_ids=eligible_ids,
        programme_candidates=programme_candidates,
    )
    return PopulationConstructionResult(
        temporal_manifest,
        membership,
        diagnostics,
        MatchedReferencePopulation(static_reference_manifest, static_reference_membership),
    )


def reject_attack_sensitive_request() -> None:
    raise CapabilityError(
        "Edge sensor groups do not support attack-sensitive client metrics",
        subject=_SENSOR_POPULATION,
        reason="attack rows are unassigned to benign sensor identities",
    )


def reject_family_thresholding() -> None:
    raise CapabilityError(
        "Edge sensor groups prohibit family thresholding",
        subject=_SENSOR_POPULATION,
        reason="no audited Edge family taxonomy exists",
    )


def _finalize_temporal_manifest(
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
    programme_candidates: tuple[str, ...],
    accepted_ids: tuple[str, ...],
    excluded_ids: tuple[str, ...],
    membership: pl.DataFrame,
) -> PopulationManifest:
    return finalize_population(
        PopulationFinalizationRequest(
            population=_TEMPORAL_POPULATION,
            dataset=DatasetId.EDGE_IIOTSET,
            identity_kind=_TEMPORAL_IDENTITY,
            declaration=EDGE_TEMPORAL_GROUPS,
            capabilities=build_population_capabilities(
                EDGE_TEMPORAL_GROUPS,
                population_evidence_role(_TEMPORAL_POPULATION),
                EDGE_IIOTSET_CAPABILITIES,
            ),
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=programme_candidates,
            accepted_ids=accepted_ids,
            excluded_ids=excluded_ids,
            expected_identities=programme_candidates,
            chronology_required=True,
            membership=select_membership_frame(membership),
            canonical_schema_checksum=EDGE_SCHEMA.checksum,
        )
    )


def _chronology_eligibility(
    canonical_root: Path,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[ChronologyExclusionReason, ...], int]:
    manifest_path = Path(canonical_root) / CanonicalPublicationArtifact.MANIFEST
    if not manifest_path.is_file():
        raise DataIntegrityError(
            "Edge canonical manifest is required for temporal eligibility",
            subject=_TEMPORAL_POPULATION,
            reason="chronology must be read from persisted evidence",
        )
    document = CanonicalManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    eligible: list[str] = []
    excluded: list[str] = []
    reasons: list[ChronologyExclusionReason] = []
    duplicate_total = 0
    for group in sorted(EDGE_BENIGN_SENSOR_GROUPS):
        group_id = group.value
        if group is EdgeSensorGroup.MODBUS:
            excluded.append(group_id)
            reasons.append(ChronologyExclusionReason.MODBUS_ADDRESS_LITERAL)
            continue
        evidence = _chronology_for_group(group_id, document.chronology)
        if evidence is None:
            excluded.append(group_id)
            reasons.append(ChronologyExclusionReason.CANONICAL_CHRONOLOGY_MISSING)
            continue
        duplicate_total += evidence.duplicate_timestamp_count.value
        if evidence.temporal_eligible:
            eligible.append(group_id)
        else:
            excluded.append(group_id)
            reasons.append(ChronologyExclusionReason.CANONICAL_CHRONOLOGY_INELIGIBLE)
    return tuple(eligible), tuple(excluded), tuple(reasons), duplicate_total


def _chronology_for_group(group_id: str, chronology):
    for item in chronology:
        if item.group_identity == group_id:
            return item
    return None


def _load_static_membership(canonical_root: Path) -> pl.DataFrame:
    paths = sorted(
        canonical_branch_directory(canonical_root, EdgeAssetRole.STATIC_BENIGN).glob(PartitioningFilePattern.PARQUET)
    )
    if not paths:
        raise DataIntegrityError(
            "Edge static benign assets are missing",
            subject=_SENSOR_POPULATION,
            reason="static population construction requires published static_benign parquet assets",
        )
    frame = (
        pl.scan_parquet([str(path) for path in paths])
        .select(
            pl.col(_GROUP).alias(CLIENT_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.STABLE_ROW_ID).alias(STABLE_ROW_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).alias(SOURCE_ROW_INDEX_COLUMN),
            pl.lit(PopulationOutcomeLabel.BENIGN.value).alias(OUTCOME_LABEL_COLUMN),
        )
        .collect(engine="streaming")
        .sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    )
    return select_membership_frame(frame)


def _load_temporal_membership(canonical_root: Path, eligible_ids: tuple[str, ...]) -> pl.DataFrame:
    temporal_root = canonical_branch_directory(canonical_root, EdgeAssetRole.TEMPORAL_BENIGN)
    paths = tuple(temporal_root / f"{group_id}.parquet" for group_id in eligible_ids)
    missing = tuple(path.name for path in paths if not path.is_file())
    if missing:
        raise DataIntegrityError(
            "temporal assets are missing for chronology-eligible groups",
            subject=_TEMPORAL_POPULATION,
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
            subject=_TEMPORAL_POPULATION,
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
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_TEMPORAL_POPULATION,
            dataset=DatasetId.EDGE_IIOTSET,
            identity_kind=_TEMPORAL_IDENTITY,
            declaration=EDGE_TEMPORAL_GROUPS,
            capabilities=build_population_capabilities(
                EDGE_TEMPORAL_GROUPS,
                population_evidence_role(_TEMPORAL_POPULATION),
                EDGE_IIOTSET_CAPABILITIES,
            ),
            partition_seed=partition_seed,
            split_protocol=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
            candidate_ids=programme_candidates,
            accepted_ids=eligible_ids,
            excluded_ids=excluded,
            expected_identities=programme_candidates,
            chronology_required=True,
            membership=membership,
            canonical_schema_checksum=EDGE_SCHEMA.checksum,
        )
    )
    return manifest, membership
