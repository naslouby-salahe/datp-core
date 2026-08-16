from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.core.errors import (
    CapabilityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ClientIdentityToken,
    DatasetId,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.core.numeric import Seed
from datp_core.data.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.data.ciciot2023.schema import (
    CICIoT2023ArtifactName,
    CICIoT2023Column,
    CICIoT2023EligibilityReason,
    CICIoT2023NormalizedLabel,
)
from datp_core.data.contracts import CanonicalProvenanceColumn
from datp_core.data.populations.construction import PopulationFinalizationRequest, finalize_population
from datp_core.data.populations.contracts import (
    CICIOT_FILE_CLIENTS,
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    SOURCE_PATH_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationConstructionEvidence,
    PopulationConstructionResult,
    PopulationOutcomeLabel,
    build_population_capabilities,
    population_evidence_role,
    select_membership_frame,
)
from datp_core.data.populations.paths import canonical_data_glob

_ELIGIBLE = CICIoT2023Column.MODEL_INPUT_ELIGIBLE
_LABEL = CICIoT2023Column.LABEL
_POPULATION = PopulationId.CICIOT_FILE_CLIENTS
_IDENTITY = PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS
_CSV_SUFFIX_PATTERN = CICIoT2023ArtifactName.CSV_SUFFIX.value.replace(".", r"\.")


def _client_id_from_source_path_expression() -> pl.Expr:
    return (
        pl.col(SOURCE_PATH_COLUMN)
        .str.split("/")
        .list.last()
        .str.replace_all(_CSV_SUFFIX_PATTERN, "")
        .alias(CLIENT_ID_COLUMN)
    )


class CICIoT2023PopulationViolation(StrEnum):
    TEMPORAL_INTERPRETATION_UNSUPPORTED = "temporal_interpretation_unsupported"
    NO_ELIGIBLE_ROWS_REMAIN = "no_eligible_rows_remain"
    CANDIDATE_COUNT_MISMATCH = "candidate_count_mismatch"


def construct_ciciot_file_clients(
    canonical_root: Path,
    *,
    partition_seed: Seed,
    split_protocol: SplitProtocolId,
) -> PopulationConstructionResult:
    if split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise CapabilityError(
            ErrorMessage("CICIoT2023 file clients prohibit temporal interpretation"),
            subject=_POPULATION,
            reason=CICIoT2023PopulationViolation.TEMPORAL_INTERPRETATION_UNSUPPORTED,
        )
    candidates = _candidate_ids(canonical_root)
    eligible = _load_eligible_membership(canonical_root)
    accepted = tuple(
        ClientIdentityToken(value) for value in eligible.get_column(CLIENT_ID_COLUMN).unique().sort().to_list()
    )
    excluded = tuple(candidate for candidate in candidates if candidate not in frozenset(accepted))
    membership = select_membership_frame(eligible).sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    manifest = finalize_population(
        PopulationFinalizationRequest(
            population=_POPULATION,
            dataset=DatasetId.CICIOT2023,
            identity_kind=_IDENTITY,
            declaration=CICIOT_FILE_CLIENTS,
            capabilities=build_population_capabilities(
                CICIOT_FILE_CLIENTS,
                population_evidence_role(_POPULATION),
                CICIOT2023_CAPABILITIES,
            ),
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            candidate_ids=candidates,
            accepted_ids=accepted,
            excluded_ids=excluded,
            expected_identities=candidates,
            chronology_required=False,
            membership=membership,
        )
    )
    excluded_rows = _ciciot_excluded_row_evidence(canonical_root)
    evidence = PopulationConstructionEvidence(
        excluded_rows=excluded_rows,
        client_eligibility=_ciciot_client_eligibility_evidence(excluded_rows),
    )
    return PopulationConstructionResult(manifest, membership, None, None, evidence)


def _ciciot_excluded_row_evidence(canonical_root: Path) -> pl.DataFrame:
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
        .with_columns(_client_id_from_source_path_expression())
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


def _ciciot_client_eligibility_evidence(excluded_rows: pl.DataFrame) -> pl.DataFrame:
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


def _load_eligible_membership(canonical_root: Path) -> pl.DataFrame:
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
            _client_id_from_source_path_expression(),
            pl.when(pl.col(_LABEL) == CICIoT2023NormalizedLabel.BENIGN)
            .then(pl.lit(PopulationOutcomeLabel.BENIGN.value))
            .otherwise(pl.lit(PopulationOutcomeLabel.ATTACK.value))
            .alias(OUTCOME_LABEL_COLUMN),
        )
        .collect(engine="streaming")
    )
    if frame.height == 0:
        raise ScientificContractError(
            ErrorMessage("no CICIoT2023 rows remain after the model-input eligibility gate"),
            subject=_POPULATION,
            reason=CICIoT2023PopulationViolation.NO_ELIGIBLE_ROWS_REMAIN,
        )
    return frame


def _candidate_ids(canonical_root: Path) -> tuple[ClientIdentityToken, ...]:
    candidates = tuple(
        ClientIdentityToken(value)
        for value in (
            pl.scan_parquet(canonical_data_glob(canonical_root))
            .select(pl.col(CanonicalProvenanceColumn.SOURCE_PATH).alias(SOURCE_PATH_COLUMN))
            .with_columns(_client_id_from_source_path_expression())
            .select(CLIENT_ID_COLUMN)
            .unique()
            .sort(CLIENT_ID_COLUMN)
            .collect(engine="streaming")
            .get_column(CLIENT_ID_COLUMN)
            .to_list()
        )
    )
    if len(candidates) != CICIOT_FILE_CLIENTS.client_count.value:
        raise ScientificContractError(
            ErrorMessage("CICIoT2023 source-file candidate count disagrees with the audited population"),
            subject=_POPULATION,
            reason=CICIoT2023PopulationViolation.CANDIDATE_COUNT_MISMATCH,
        )
    return candidates
