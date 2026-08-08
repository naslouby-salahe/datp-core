"""CICIoT2023 file-defined pseudo-client preprocessing."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.data.populations.contracts import (
    CLIENT_ID_COLUMN,
    PARTITION_ROLE_COLUMN,
    SOURCE_PATH_COLUMN,
    STABLE_ROW_ID_COLUMN,
)
from datp_core.data.preprocessing.artifact_validation import extract_partitions
from datp_core.data.preprocessing.artifacts import PartitionOrdering
from datp_core.data.preprocessing.client_partitions import (
    CANONICAL_DATA_DIRECTORY,
    PARQUET_PATTERN,
    estimator_for_client,
)
from datp_core.data.preprocessing.federated import fit_estimators_for_federated_clients, publish_client_preprocessing
from datp_core.data.preprocessing.models import (
    ClientPreprocessingResult,
    ClientPublishRequest,
    FederatedPreprocessingOutcome,
    PreprocessingPublishContext,
)
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import ContractSubject, DatasetId, ProcessedDataBranch, PublicationStatus
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import ClientPublicationCount
from datp_core.domain.values.identifiers import FeatureNameSequence
from datp_core.domain.values.paths import ClientPathToken
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


@dataclass(frozen=True, slots=True)
class _CanonicalSourceFile:
    source_path: str
    parquet_path: Path


def ciciot_source_files(
    canonical_root: Path,
) -> tuple[_CanonicalSourceFile, ...]:
    sources = tuple(
        _CanonicalSourceFile(
            source_path=str(
                pl.read_parquet(
                    path,
                    columns=[SOURCE_PATH_COLUMN],
                    n_rows=1,
                ).item(0, 0)
            ),
            parquet_path=path,
        )
        for path in sorted((canonical_root / CANONICAL_DATA_DIRECTORY).glob(PARQUET_PATTERN))
    )
    if not sources:
        raise ScientificContractError(
            "CIC canonical files are unavailable",
            subject=DatasetId.CICIOT2023,
        )
    source_paths = tuple(source.source_path for source in sources)
    if len(set(source_paths)) != len(source_paths):
        raise ScientificContractError(
            "CIC canonical source paths must be unique",
            subject=DatasetId.CICIOT2023,
        )
    return sources


def canonical_source_file(
    source_files: tuple[_CanonicalSourceFile, ...],
    source_path: str,
) -> _CanonicalSourceFile:
    for source in source_files:
        if source.source_path == source_path:
            return source
    raise ScientificContractError(
        "file-defined client source must resolve exactly once",
        subject=ContractSubject.CLIENT_IDENTITY,
    )


def single_client_source_path(assignments: pl.DataFrame) -> str:
    sources = assignments.get_column(SOURCE_PATH_COLUMN).unique().to_list()
    if len(sources) != 1:
        raise ScientificContractError(
            "file-defined client assignments must originate from exactly one source file",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return str(sources[0])


def preprocess_ciciot_client_local(
    *,
    context: PreprocessingPublishContext,
    assignments: pl.DataFrame,
    canonical_root: Path,
    feature_names: FeatureNameSequence,
    identity: ExternalTemporalExecutionIdentity,
) -> FederatedPreprocessingOutcome:
    source_files = ciciot_source_files(canonical_root)

    client_id_vals = sorted(str(value) for value in assignments.get_column(CLIENT_ID_COLUMN).unique().to_list())
    grouped_assignments = {str(k): v for k, v in assignments.partition_by(CLIENT_ID_COLUMN, as_dict=True).items()}

    publications: list[ClientPreprocessingResult] = []
    published_count = 0
    reused_count = 0
    feature_cache: dict[str, pl.DataFrame] = {}

    for client_str in client_id_vals:
        client_id = ClientPathToken(client_str)
        client_assignments = grouped_assignments[client_str]
        source_path = single_client_source_path(client_assignments)

        if source_path not in feature_cache:
            source_file = canonical_source_file(source_files, source_path)
            feature_cache[source_path] = pl.read_parquet(
                source_file.parquet_path,
                columns=[STABLE_ROW_ID_COLUMN, *feature_names],
            )

        features = feature_cache[source_path]

        joined = client_assignments.join(
            features,
            on=STABLE_ROW_ID_COLUMN,
            how="inner",
        ).sort((PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN))

        if joined.height != client_assignments.height:
            raise ScientificContractError(
                "canonical feature join lost file-client assignment rows",
                subject=identity.population,
            )

        partitions = extract_partitions(
            joined,
            feature_names,
            split_protocol=context.split_protocol_identity,
            branch=ProcessedDataBranch.FEDERATED,
            ordering=PartitionOrdering.PRESERVE_SOURCE_ORDER,
        )

        collection = ClientCollection((ClientOwned(client_id, partitions),))
        estimators = fit_estimators_for_federated_clients(
            context.protocol,
            collection,
        )
        estimator = estimator_for_client(estimators, client_id)
        publication = publish_client_preprocessing(
            ClientPublishRequest(
                context,
                client_id,
                estimator,
                partitions,
            )
        )

        if publication.publication_status is PublicationStatus.REUSED:
            reused_count += 1
        else:
            published_count += 1
        publications.append(publication)

    return FederatedPreprocessingOutcome(
        population=identity.population,
        dataset=DatasetId.CICIOT2023,
        partition_seed=context.partition_seed,
        split_protocol=context.split_protocol_identity,
        preprocessing_identity=context.protocol.identity,
        client_publications=tuple(publications),
        published_count=ClientPublicationCount(published_count),
        reused_count=ClientPublicationCount(reused_count),
        execution_identity=identity,
    )
