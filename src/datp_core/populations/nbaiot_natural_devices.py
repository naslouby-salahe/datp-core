"""N-BaIoT natural physical-device population construction."""

from pathlib import Path

import polars as pl

from datp_core.datasets.models import CanonicalProvenanceColumn
from datp_core.datasets.nbaiot.schema import (
    NBAIOT_DEVICE_IDENTITIES,
    NBAIOT_SCHEMA,
    NBaIoTCanonicalColumn,
    NBaIoTSourceLabel,
)
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.domain.errors import DataIntegrityError
from datp_core.domain.values import Seed
from datp_core.populations.capabilities import population_declaration
from datp_core.populations.integrity import (
    assess_declared_feasibility,
    membership_frame_checksum,
    outcome_row_counts,
    validate_population_manifest,
)
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    FAMILY_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationManifestSpec,
    PopulationOutcomeLabel,
    build_population_manifest,
    canonical_data_glob,
    select_membership_frame,
)

_SOURCE_CLIENT = NBaIoTCanonicalColumn.PHYSICAL_CLIENT_ID
_SOURCE_FAMILY = NBaIoTCanonicalColumn.PHYSICAL_DEVICE_FAMILY
_SOURCE_LABEL = NBaIoTCanonicalColumn.RAW_LABEL
_POPULATION = PopulationId.NBAIOT_NATURAL_DEVICES
_IDENTITY = PopulationIdentityKind.PHYSICAL_DEVICES


def build_nbaiot_natural_devices(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> tuple[PopulationManifest, pl.DataFrame]:
    declaration = population_declaration(_POPULATION)
    frame = _load_identity_frame(canonical_root)
    candidates = tuple(sorted(NBAIOT_DEVICE_IDENTITIES))
    observed = tuple(frame.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    if observed != candidates:
        raise DataIntegrityError(
            "N-BaIoT physical-client identities disagree with the audited set",
            subject=_POPULATION,
            reason="natural-device construction requires exactly the nine audited devices",
        )
    membership = select_membership_frame(frame).sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    family_by_client = tuple(
        (str(client_id), str(family))
        for client_id, family in frame.select([CLIENT_ID_COLUMN, FAMILY_ID_COLUMN])
        .unique()
        .sort(CLIENT_ID_COLUMN)
        .iter_rows()
    )
    benign, attack = outcome_row_counts(membership)
    feasibility = assess_declared_feasibility(
        expected_count=declaration.client_count.value,
        candidate_ids=candidates,
        accepted_ids=candidates,
        expected_identities=candidates,
        chronology_required=False,
    )
    manifest = build_population_manifest(
        PopulationManifestSpec(
            population=_POPULATION,
            dataset=DatasetId.NBAIOT,
            identity_kind=_IDENTITY,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_clients=candidates,
            accepted_clients=candidates,
            excluded_client_ids=(),
            total_membership_rows=membership.height,
            benign_row_count=benign,
            attack_row_count=attack,
            membership_checksum=membership_frame_checksum(membership),
            canonical_schema_checksum=NBAIOT_SCHEMA.checksum,
            feasibility=feasibility,
            family_by_client=family_by_client,
        )
    )
    validate_population_manifest(manifest, membership)
    return manifest, membership


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
            "N-BaIoT rows with unrecognized labels cannot enter the natural population",
            subject=_POPULATION,
            reason="only audited benign and attack labels are admissible",
        )
    return frame
