"""CICIoT2023 file-defined pseudo-client population construction."""

from pathlib import Path

import polars as pl

from datp_core.datasets.ciciot2023.schema import (
    CICIOT2023_SCHEMA,
    CICIoT2023ArtifactName,
    CICIoT2023Column,
    CICIoT2023NormalizedLabel,
)
from datp_core.datasets.models import CanonicalProvenanceColumn
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.domain.errors import CapabilityError, DataIntegrityError, ScientificContractError
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
    OUTCOME_LABEL_COLUMN,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationManifest,
    PopulationManifestSpec,
    PopulationOutcomeLabel,
    build_population_manifest,
    canonical_data_glob,
    select_membership_frame,
)

_ELIGIBLE = CICIoT2023Column.MODEL_INPUT_ELIGIBLE
_LABEL = CICIoT2023Column.LABEL
_POPULATION = PopulationId.CICIOT_FILE_CLIENTS
_IDENTITY = PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS


def build_ciciot_file_clients(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> tuple[PopulationManifest, pl.DataFrame]:
    if split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise CapabilityError(
            "CICIoT2023 file clients prohibit temporal interpretation",
            subject=_POPULATION,
            reason="merged files retain no audited capture chronology",
        )
    declaration = population_declaration(_POPULATION)
    eligible = _load_eligible_membership(canonical_root)
    candidates = tuple(eligible.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    if len(candidates) != declaration.client_count.value:
        raise DataIntegrityError(
            "CICIoT2023 file-client count disagrees with the audited merged-file catalogue",
            subject=_POPULATION,
            reason="file-defined clients must equal the locked merged-file count",
        )
    membership = select_membership_frame(eligible).sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    benign, attack = outcome_row_counts(membership)
    feasibility = assess_declared_feasibility(
        expected_count=declaration.client_count.value,
        candidate_ids=candidates,
        accepted_ids=candidates,
        expected_identities=None,
        chronology_required=False,
    )
    manifest = build_population_manifest(
        PopulationManifestSpec(
            population=_POPULATION,
            dataset=DatasetId.CICIOT2023,
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
            canonical_schema_checksum=CICIOT2023_SCHEMA.checksum,
            feasibility=feasibility,
        )
    )
    validate_population_manifest(manifest, membership)
    return manifest, membership


def reject_physical_device_interpretation() -> None:
    raise CapabilityError(
        "CICIoT2023 cannot be interpreted as physical devices",
        subject=_POPULATION,
        reason="merged artifacts preserve only file-defined pseudo-client identities",
    )


def reject_family_interpretation() -> None:
    raise CapabilityError(
        "CICIoT2023 cannot support family thresholding",
        subject=_POPULATION,
        reason="no physical-device family taxonomy survives in the merged files",
    )


def _load_eligible_membership(canonical_root: Path) -> pl.DataFrame:
    csv_suffix = CICIoT2023ArtifactName.CSV_SUFFIX.value.replace(".", r"\.")
    frame = (
        pl.scan_parquet(canonical_data_glob(canonical_root))
        .select(
            pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN),
            pl.col(CanonicalProvenanceColumn.STABLE_ROW_ID).alias(STABLE_ROW_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).alias(SOURCE_ROW_INDEX_COLUMN),
            pl.col(_LABEL),
            pl.col(_ELIGIBLE),
        )
        .filter(pl.col(_ELIGIBLE))
        .with_columns(
            pl.col(SOURCE_PATH_COLUMN)
            .str.split("/")
            .list.last()
            .str.replace_all(csv_suffix, "")
            .alias(CLIENT_ID_COLUMN),
            pl.when(pl.col(_LABEL) == CICIoT2023NormalizedLabel.BENIGN)
            .then(pl.lit(PopulationOutcomeLabel.BENIGN.value))
            .otherwise(pl.lit(PopulationOutcomeLabel.ATTACK.value))
            .alias(OUTCOME_LABEL_COLUMN),
        )
        .collect(engine="streaming")
    )
    if frame.height == 0:
        raise ScientificContractError(
            "no CICIoT2023 rows remain after the model-input eligibility gate",
            subject=_POPULATION,
            reason="eligibility exclusions must leave at least one admissible model-input row",
        )
    return frame
