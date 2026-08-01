"""CICIoT2023 file-defined pseudo-client population construction."""

from pathlib import Path

import polars as pl

from datp_core.datasets.ciciot2023.schema import (
    CICIOT2023_SCHEMA,
    CICIoT2023ArtifactName,
    CICIoT2023Column,
    CICIoT2023EligibilityReason,
    CICIoT2023NormalizedLabel,
)
from datp_core.datasets.models import CanonicalProvenanceColumn
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.domain.errors import CapabilityError, ScientificContractError
from datp_core.domain.values import Seed
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
    PopulationManifest,
    PopulationOutcomeLabel,
    canonical_data_glob,
    select_membership_frame,
)

_ELIGIBLE = CICIoT2023Column.MODEL_INPUT_ELIGIBLE
_LABEL = CICIoT2023Column.LABEL
_POPULATION = PopulationId.CICIOT_FILE_CLIENTS
_IDENTITY = PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS


def ciciot_excluded_row_evidence(canonical_root: Path) -> pl.DataFrame:
    """Return canonical rows rejected by the immutable model-input eligibility policy."""
    csv_suffix = CICIoT2023ArtifactName.CSV_SUFFIX.value.replace(".", r"\.")
    return (
        pl.scan_parquet(canonical_data_glob(canonical_root))
        .select(
            pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN),
            pl.col(CanonicalProvenanceColumn.STABLE_ROW_ID).alias(STABLE_ROW_ID_COLUMN),
            pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).alias(SOURCE_ROW_INDEX_COLUMN),
            pl.col(CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL),
            pl.col(CICIoT2023EligibilityReason.NONFINITE_FEATURE),
            pl.col(_ELIGIBLE),
        )
        .filter(~pl.col(_ELIGIBLE))
        .with_columns(
            pl.col(SOURCE_PATH_COLUMN)
            .str.split("/")
            .list.last()
            .str.replace_all(csv_suffix, "")
            .alias(CLIENT_ID_COLUMN)
        )
        .drop(_ELIGIBLE)
        .select(
            CLIENT_ID_COLUMN,
            STABLE_ROW_ID_COLUMN,
            SOURCE_PATH_COLUMN,
            SOURCE_ROW_INDEX_COLUMN,
            CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL,
            CICIoT2023EligibilityReason.NONFINITE_FEATURE,
        )
        .collect(engine="streaming")
        .sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    )


def ciciot_client_eligibility_evidence(excluded_rows: pl.DataFrame) -> pl.DataFrame:
    """Aggregate typed canonical exclusion reasons by audited file-defined client."""
    return (
        excluded_rows.group_by(CLIENT_ID_COLUMN)
        .agg(
            pl.len().alias("excluded_row_count"),
            pl.col(CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL)
            .sum()
            .cast(pl.UInt64)
            .alias(CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL),
            pl.col(CICIoT2023EligibilityReason.NONFINITE_FEATURE)
            .sum()
            .cast(pl.UInt64)
            .alias(CICIoT2023EligibilityReason.NONFINITE_FEATURE),
        )
        .sort(CLIENT_ID_COLUMN)
    )


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
    candidates = _candidate_ids(canonical_root)
    eligible = _load_eligible_membership(canonical_root)
    accepted = tuple(eligible.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    excluded = tuple(candidate for candidate in candidates if candidate not in frozenset(accepted))
    membership = select_membership_frame(eligible).sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_POPULATION,
            dataset=DatasetId.CICIOT2023,
            identity_kind=_IDENTITY,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=candidates,
            accepted_ids=accepted,
            excluded_ids=excluded,
            expected_identities=candidates,
            chronology_required=False,
            membership=membership,
            canonical_schema_checksum=CICIOT2023_SCHEMA.checksum,
        )
    )
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


def _candidate_ids(canonical_root: Path) -> tuple[str, ...]:
    csv_suffix = CICIoT2023ArtifactName.CSV_SUFFIX.value.replace(".", r"\.")
    candidates = tuple(
        pl.scan_parquet(canonical_data_glob(canonical_root))
        .select(pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN))
        .with_columns(
            pl.col(SOURCE_PATH_COLUMN)
            .str.split("/")
            .list.last()
            .str.replace_all(csv_suffix, "")
            .alias(CLIENT_ID_COLUMN)
        )
        .select(CLIENT_ID_COLUMN)
        .unique()
        .sort(CLIENT_ID_COLUMN)
        .collect(engine="streaming")
        .get_column(CLIENT_ID_COLUMN)
        .to_list()
    )
    expected_count = population_declaration(_POPULATION).client_count.value
    if len(candidates) != expected_count:
        raise ScientificContractError(
            "CICIoT2023 source-file candidate count disagrees with the audited population",
            subject=_POPULATION,
            reason="file identity must remain the exact audited pseudo-client boundary",
        )
    return candidates
