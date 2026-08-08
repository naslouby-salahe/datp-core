"""Matched static-reference scoring inputs for temporal experiments."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    ContractSubject,
    DatasetId,
    FeatureNameSequence,
    PartitionRole,
    SplitProtocolId,
    TemporalState,
)
from datp_core.data.edge_iiotset.schema import EdgeAssetRole
from datp_core.data.populations.contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    SplitManifestDocument,
)
from datp_core.data.preprocessing.artifact_validation import transform_feature_matrix
from datp_core.data.preprocessing.client_partitions import CANONICAL_DATA_DIRECTORY, PARQUET_PATTERN
from datp_core.data.preprocessing.models import ClientPreprocessingResult
from datp_core.data.preprocessing.persisted_artifacts import (
    MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET,
    MATCHED_STATIC_SPLIT_MANIFEST_ASSET,
)
from datp_core.data.preprocessing.state import TrustedScaler, load_estimator
from datp_core.detector.scoring.models import ClientScoringInput
from datp_core.pipeline.execution.context import FederatedExecutionContext, training_feature_names
from datp_core.pipeline.execution.layout import ExecutionArtifactDirectory, bounded_evidence_seed_directory
from datp_core.runtime.configuration import DATA_ROOT


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchedStaticReferenceInputs:
    clients: tuple[ClientScoringInput, ...]
    split_manifest_checksum: Checksum


def matched_static_reference_inputs(
    context: FederatedExecutionContext,
    output_root: Path,
) -> MatchedStaticReferenceInputs:
    identity = context.execution_identity
    if (
        identity is None
        or identity.population is not context.coordinate.population
        or identity.temporal_state not in (TemporalState.FROZEN_FUTURE, TemporalState.RECALIBRATED_FUTURE)
        or context.coordinate.split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    ):
        raise ScientificContractError(
            "matched static scoring requires a temporal historical execution context",
            subject=context.coordinate.population,
        )
    root = bounded_evidence_seed_directory(identity, context.coordinate.training_seed, output_root)
    split_directory = root / ExecutionArtifactDirectory.SPLIT
    try:
        split_manifest = SplitManifestDocument.model_validate_json(
            (split_directory / MATCHED_STATIC_SPLIT_MANIFEST_ASSET).read_text(encoding="utf-8")
        )
        assignments = pl.read_parquet(split_directory / MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET)
    except (OSError, ValueError, pl.exceptions.PolarsError) as error:
        raise ScientificContractError(
            "matched static split artifacts are missing or invalid",
            subject=context.coordinate.population,
        ) from error
    if split_manifest.split_protocol is not SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE:
        raise ScientificContractError(
            "matched static scoring requires the random-fractional static split",
            subject=split_manifest.split_protocol,
        )
    feature_names = training_feature_names(DatasetId.EDGE_IIOTSET)
    canonical_root = DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / DatasetId.EDGE_IIOTSET.value
    feature_scan = pl.scan_parquet(
        str(canonical_root / CANONICAL_DATA_DIRECTORY / EdgeAssetRole.TEMPORAL_BENIGN.value / PARQUET_PATTERN)
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
        .sort((CLIENT_ID_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN))
    )
    if joined.height != assignments.height:
        raise ScientificContractError(
            "matched static canonical feature join lost assignment rows",
            subject=context.coordinate.population,
        )
    observed_clients = frozenset(str(value) for value in joined.get_column(CLIENT_ID_COLUMN).unique().to_list())
    expected_clients = frozenset(client.client_id for client in context.clients)
    if observed_clients != expected_clients:
        raise ScientificContractError(
            "matched static and temporal client inventories must be identical",
            subject=context.coordinate.population,
        )
    return MatchedStaticReferenceInputs(
        clients=tuple(
            _matched_static_client_input(
                joined=joined,
                client=client,
                publication=_client_publication(context.preprocessing.client_publications, client),
                feature_names=feature_names,
            )
            for client in sorted(context.clients)
        ),
        split_manifest_checksum=split_manifest.assignment_checksum,
    )


def _matched_static_client_input(
    *,
    joined: pl.DataFrame,
    client: ClientIdentity,
    publication: ClientPreprocessingResult,
    feature_names: FeatureNameSequence,
) -> ClientScoringInput:
    state = publication.fitted_state
    if state.protocol.input_feature_names != feature_names:
        raise ScientificContractError(
            "historical preprocessing schema does not match the static scoring schema",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    estimator = load_estimator(state.estimator_path, state.protocol.estimator_class_name)
    return ClientScoringInput(
        client=client,
        calibration_features=_transform_matched_static_partition(
            joined,
            client,
            PartitionRole.CALIBRATION,
            feature_names,
            estimator,
        ),
        evaluation_features=_transform_matched_static_partition(
            joined,
            client,
            PartitionRole.EVALUATION,
            feature_names,
            estimator,
        ),
    )


def _transform_matched_static_partition(
    joined: pl.DataFrame,
    client: ClientIdentity,
    role: PartitionRole,
    feature_names: FeatureNameSequence,
    estimator: TrustedScaler,
) -> pl.DataFrame:
    source = joined.filter(
        (pl.col(CLIENT_ID_COLUMN) == client.client_id) & (pl.col(PARTITION_ROLE_COLUMN).cast(pl.String) == role.value)
    ).select((STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names.names))
    if source.is_empty():
        raise ScientificContractError(
            f"matched static {role.value} partition is empty for {client.client_id}",
            subject=role,
        )
    transformed = transform_feature_matrix(
        estimator,
        source.select(feature_names.as_list()).to_numpy(),
        feature_names,
        role,
        description=f"matched static {role.value} matrix",
    )
    return source.select((STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN)).hstack(
        pl.from_numpy(transformed, schema=feature_names.as_list())
    )


def _client_publication(
    publications: tuple[ClientPreprocessingResult, ...],
    client: ClientIdentity,
) -> ClientPreprocessingResult:
    matches = tuple(item for item in publications if item.client_identity.value == client.client_id)
    if len(matches) != 1:
        raise ScientificContractError(
            f"expected one historical preprocessing state for {client.client_id}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]
