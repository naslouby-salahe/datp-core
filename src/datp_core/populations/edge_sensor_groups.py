"""Edge-IIoTset static benign sensor-group population construction."""

from pathlib import Path

import polars as pl

from datp_core.datasets.edge_iiotset.schema import (
    EDGE_BENIGN_SENSOR_GROUPS,
    EDGE_SCHEMA,
    EdgeAssetRole,
    EdgeCanonicalColumn,
)
from datp_core.datasets.models import CanonicalProvenanceColumn
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.domain.errors import CapabilityError, DataIntegrityError
from datp_core.domain.values import Seed
from datp_core.populations.integrity import (
    PopulationFinalizationRequest,
    finalize_population,
)
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARQUET_GLOB,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationManifest,
    PopulationOutcomeLabel,
    canonical_branch_directory,
    select_membership_frame,
)

_GROUP = EdgeCanonicalColumn.BENIGN_SENSOR_GROUP
_POPULATION = PopulationId.EDGE_SENSOR_GROUPS
_IDENTITY = PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS


def build_edge_sensor_groups(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> tuple[PopulationManifest, pl.DataFrame]:
    if split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise CapabilityError(
            "static Edge sensor groups do not use chronological splits",
            subject=_POPULATION,
            reason="temporal analysis uses EDGE_TEMPORAL_GROUPS exclusively",
        )
    candidates = tuple(group.value for group in EDGE_BENIGN_SENSOR_GROUPS)
    membership = _load_static_membership(canonical_root)
    observed = tuple(membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    expected = tuple(sorted(candidates))
    if observed != expected:
        raise DataIntegrityError(
            "Edge static sensor-group identities disagree with the audited set",
            subject=_POPULATION,
            reason="static construction requires exactly the ten audited benign folders",
        )
    if membership.filter(pl.col(OUTCOME_LABEL_COLUMN) != PopulationOutcomeLabel.BENIGN).height > 0:
        raise DataIntegrityError(
            "Edge static sensor groups cannot carry attack rows",
            subject=_POPULATION,
            reason="attack traffic remains unassigned to sensor identities",
        )
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_POPULATION,
            dataset=DatasetId.EDGE_IIOTSET,
            identity_kind=_IDENTITY,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=expected,
            accepted_ids=expected,
            excluded_ids=(),
            expected_identities=expected,
            chronology_required=False,
            membership=membership,
            canonical_schema_checksum=EDGE_SCHEMA.checksum,
        )
    )
    return manifest, membership


def reject_attack_sensitive_request() -> None:
    raise CapabilityError(
        "Edge sensor groups do not support attack-sensitive client metrics",
        subject=_POPULATION,
        reason="attack rows are unassigned to benign sensor identities",
    )


def reject_family_thresholding() -> None:
    raise CapabilityError(
        "Edge sensor groups prohibit family thresholding",
        subject=_POPULATION,
        reason="no audited Edge family taxonomy exists",
    )


def _load_static_membership(canonical_root: Path) -> pl.DataFrame:
    paths = sorted(canonical_branch_directory(canonical_root, EdgeAssetRole.STATIC_BENIGN).glob(PARQUET_GLOB))
    if not paths:
        raise DataIntegrityError(
            "Edge static benign assets are missing",
            subject=_POPULATION,
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
