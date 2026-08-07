"""Client partition preparation shared by direct and published-artifact preprocessing."""

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
from datp_core.domain.values.identifiers import FeatureName, FeatureNameSequence
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

CANONICAL_DATA_DIRECTORY = "data"
PARQUET_PATTERN = "*.parquet"

_EDGE_PUBLISHED_POPULATIONS = frozenset(
    {
        PopulationId.EDGE_TEMPORAL_GROUPS,
        PopulationId.EDGE_SENSOR_GROUPS,
    }
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
) -> pl.DataFrame:
    if identity.population not in _EDGE_PUBLISHED_POPULATIONS:
        return join_handoff_with_canonical_features(
            canonical_root,
            handoff,
            feature_names,
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
) -> pl.DataFrame:
    eligible_expr = pl.all_horizontal(tuple(pl.col(name).is_finite().fill_null(False) for name in feature_names))
    eligible = joined.filter(eligible_expr)
    excluded_row_count = joined.height - eligible.height
    if excluded_row_count:
        structlog.get_logger("datp_core.preprocessing").warning(
            "edge_model_input_rows_excluded_nonfinite",
            dataset=dataset.value,
            population=population.value,
            excluded_row_count=excluded_row_count,
            total_row_count=joined.height,
        )
    return eligible


def model_feature_names(
    dataset: DatasetId,
    feature_names: tuple[str, ...],
) -> FeatureNameSequence:
    if dataset is not DatasetId.EDGE_IIOTSET:
        return FeatureNameSequence(tuple(FeatureName(name) for name in feature_names))
    if frozenset(EDGE_NUMERIC_FEATURE_COLUMNS) - frozenset(feature_names):
        raise ScientificContractError("Edge numeric feature declaration must be a canonical feature subset")
    return FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))
