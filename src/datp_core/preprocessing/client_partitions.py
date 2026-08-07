"""Client partition preparation shared by direct and published-artifact preprocessing."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
import structlog

from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS, EdgeAssetRole
from datp_core.datasets.partitioning.construction import join_handoff_with_canonical_features
from datp_core.datasets.partitioning.contracts import (
    CLIENT_ID_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PreprocessingHandoff,
)
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import DatasetId, PopulationId, ProcessedDataBranch, PublicationStatus, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.identifiers import FeatureName, FeatureNameSequence, StableRowId
from datp_core.domain.values.paths import ClientPathToken
from datp_core.preprocessing.contracts import PartitionOrdering
from datp_core.preprocessing.federated import publish_client_preprocessing
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    ClientPublishRequest,
    FederatedFittedEstimators,
    PreprocessingPartitions,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.state import TrustedScaler
from datp_core.preprocessing.validation import extract_partitions
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.runtime.filesystem import write_text_atomically

CANONICAL_DATA_DIRECTORY = "data"
PARQUET_PATTERN = "*.parquet"
MODEL_INPUT_EXCLUSION_ASSET = "model_input_exclusions.json"
MODEL_INPUT_EXCLUSION_REASON = "nonfinite_or_null_numeric_model_input_feature"

_EDGE_PUBLISHED_POPULATIONS = frozenset(
    {
        PopulationId.EDGE_TEMPORAL_GROUPS,
        PopulationId.EDGE_SENSOR_GROUPS,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelInputExclusionEvidence:
    """Typed provenance for Edge model-input rows excluded after finite-feature gating."""

    dataset: DatasetId
    population: PopulationId
    excluded_stable_row_ids: tuple[StableRowId, ...]
    total_row_count: RowCount
    reason: str = MODEL_INPUT_EXCLUSION_REASON

    def __post_init__(self) -> None:
        if self.reason != MODEL_INPUT_EXCLUSION_REASON:
            raise ValueError("model-input exclusion reason must match the locked nonfinite gate")
        if len(self.excluded_stable_row_ids) != len(frozenset(self.excluded_stable_row_ids)):
            raise ValueError("excluded stable row identities must be unique")
        if self.total_row_count.value < len(self.excluded_stable_row_ids):
            raise ValueError("excluded row count cannot exceed total joined rows")

    @property
    def excluded_row_count(self) -> RowCount:
        return RowCount(len(self.excluded_stable_row_ids))

    @property
    def evidence_checksum(self) -> Checksum:
        ordered = ",".join(str(row_id) for row_id in self.excluded_stable_row_ids)
        return checksum_text(
            f"{self.dataset.value}|{self.population.value}|{self.reason}|{self.total_row_count.value}|{ordered}"
        )


def client_partitions(
    joined: pl.DataFrame,
    feature_names: FeatureNameSequence,
    split_protocol: SplitProtocolId,
) -> ClientCollection[ClientPathToken, PreprocessingPartitions]:
    client_ids = tuple(
        ClientPathToken(str(value)) for value in sorted(joined.get_column(CLIENT_ID_COLUMN).unique().to_list())
    )
    return ClientCollection(
        tuple(
            ClientOwned(
                client_id,
                extract_partitions(
                    joined.filter(pl.col(CLIENT_ID_COLUMN) == client_id.value),
                    feature_names,
                    split_protocol=split_protocol,
                    branch=ProcessedDataBranch.FEDERATED,
                    ordering=PartitionOrdering.PRESERVE_SOURCE_ORDER,
                ),
            )
            for client_id in client_ids
        )
    )


def publish_client_partitions(
    context: PreprocessingPublishContext,
    partitions: ClientCollection[
        ClientPathToken,
        PreprocessingPartitions,
    ],
    fitted_estimators: FederatedFittedEstimators,
) -> tuple[tuple[ClientPreprocessingResult, ...], int, int]:
    publications = tuple(
        publish_client_preprocessing(
            ClientPublishRequest(
                context=context,
                client_identity=item.client,
                fitted_estimator=estimator_for_client(
                    fitted_estimators,
                    item.client,
                ),
                partitions=item.value,
            )
        )
        for item in partitions.items
    )
    reused = sum(item.publication_status is PublicationStatus.REUSED for item in publications)
    return publications, len(publications) - reused, reused


def estimator_for_client(
    fitted_estimators: FederatedFittedEstimators,
    client: ClientPathToken,
) -> TrustedScaler:
    if isinstance(fitted_estimators, ClientCollection):
        return fitted_estimators.require(client)
    return fitted_estimators


def join_published_handoff(
    canonical_root: Path,
    handoff: PreprocessingHandoff,
    feature_names: FeatureNameSequence,
    identity: ExternalTemporalExecutionIdentity,
) -> tuple[pl.DataFrame, ModelInputExclusionEvidence | None]:
    if identity.population not in _EDGE_PUBLISHED_POPULATIONS:
        return (
            join_handoff_with_canonical_features(
                canonical_root,
                handoff,
                feature_names,
            ),
            None,
        )
    asset_role = (
        EdgeAssetRole.TEMPORAL_BENIGN
        if identity.population is PopulationId.EDGE_TEMPORAL_GROUPS
        else EdgeAssetRole.STATIC_BENIGN
    )
    assignments = handoff.assignments
    feature_scan = pl.scan_parquet(
        str(canonical_root / CANONICAL_DATA_DIRECTORY / asset_role.value / PARQUET_PATTERN)
    ).select(
        (
            STABLE_ROW_ID_COLUMN,
            *(pl.col(name).cast(pl.Float64, strict=True).alias(name) for name in feature_names),
        )
    )
    joined = (
        assignments.lazy()
        .join(feature_scan, on=STABLE_ROW_ID_COLUMN, how="inner")
        .collect()
        .sort(
            (
                CLIENT_ID_COLUMN,
                PARTITION_ROLE_COLUMN,
                STABLE_ROW_ID_COLUMN,
            )
        )
    )
    if joined.height != assignments.height:
        raise ScientificContractError(
            "canonical feature join lost assignment rows",
            subject=handoff.population_manifest.document.dataset,
        )
    return exclude_nonfinite_model_input_rows(
        joined,
        feature_names,
        dataset=handoff.population_manifest.document.dataset,
        population=handoff.population_manifest.document.population,
    )


def exclude_nonfinite_model_input_rows(
    joined: pl.DataFrame,
    feature_names: FeatureNameSequence,
    *,
    dataset: DatasetId,
    population: PopulationId,
) -> tuple[pl.DataFrame, ModelInputExclusionEvidence]:
    if STABLE_ROW_ID_COLUMN not in joined.columns:
        raise ScientificContractError(
            "model-input finite gate requires stable row identities",
            subject=dataset,
        )
    eligible_expr = pl.all_horizontal(tuple(pl.col(name).is_finite().fill_null(False) for name in feature_names))
    eligible = joined.filter(eligible_expr)
    excluded = joined.filter(~eligible_expr)
    excluded_ids = tuple(
        sorted(
            (StableRowId(str(value)) for value in excluded.get_column(STABLE_ROW_ID_COLUMN).to_list()),
            key=str,
        )
    )
    evidence = ModelInputExclusionEvidence(
        dataset=dataset,
        population=population,
        excluded_stable_row_ids=excluded_ids,
        total_row_count=RowCount(joined.height),
    )
    if evidence.excluded_row_count.value:
        structlog.get_logger("datp_core.preprocessing").warning(
            "edge_model_input_rows_excluded_nonfinite",
            dataset=dataset.value,
            population=population.value,
            excluded_row_count=evidence.excluded_row_count.value,
            total_row_count=joined.height,
            exclusion_evidence_checksum=evidence.evidence_checksum.value,
        )
    return eligible, evidence


def write_model_input_exclusion_evidence(destination: Path, evidence: ModelInputExclusionEvidence) -> Checksum:
    """Persist typed model-input exclusion provenance next to bounded-evidence preparation."""
    payload = {
        "dataset": evidence.dataset.value,
        "population": evidence.population.value,
        "reason": evidence.reason,
        "total_row_count": evidence.total_row_count.value,
        "excluded_row_count": evidence.excluded_row_count.value,
        "excluded_stable_row_ids": tuple(str(item) for item in evidence.excluded_stable_row_ids),
        "evidence_checksum": evidence.evidence_checksum.value,
    }
    write_text_atomically(destination, canonical_json_text(payload))
    return evidence.evidence_checksum


def model_feature_names(
    dataset: DatasetId,
    feature_names: tuple[str, ...],
) -> FeatureNameSequence:
    if dataset is not DatasetId.EDGE_IIOTSET:
        return FeatureNameSequence(tuple(FeatureName(name) for name in feature_names))
    if frozenset(EDGE_NUMERIC_FEATURE_COLUMNS) - frozenset(feature_names):
        raise ScientificContractError("Edge numeric feature declaration must be a canonical feature subset")
    return FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))
