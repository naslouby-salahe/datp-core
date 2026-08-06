"""Deterministic checksums for ordered held-out evaluation evidence."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.domain.enums import ScoreFrameColumn
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.checksums import Checksum
from datp_core.evaluation.models import ClientMetricResult
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.inference import ScoreArtifactManifest, ScoreRecord

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]

_LENGTH_PREFIX_BYTES = 8


class ClientChecksumField(StrEnum):
    EVALUATION_LABEL = "evaluation_label_checksum"
    SOURCE_ROW = "source_row_checksum"


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreColumnChecksum:
    client: ClientIdentity
    checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientEvidenceChecksum:
    client: ClientIdentity
    checksum: Checksum


def evaluation_label_checksum(labels: Sequence[PopulationOutcomeLabel]) -> Checksum:
    return ordered_text_checksum(tuple(label.value for label in labels))


def source_row_checksum(rows: Sequence[str]) -> Checksum:
    return ordered_text_checksum(tuple(rows))


def client_population_checksum(manifest: FederatedScoreArtifactManifest) -> Checksum:
    return canonical_checksum(tuple(sorted(record.scored_client for record in manifest.evaluation_records)))


def evaluation_label_set_checksum(manifest: FederatedScoreArtifactManifest) -> Checksum:
    return aggregate_score_record_checksum(manifest.evaluation_records, ScoreFrameColumn.OUTCOME_LABEL)


def evaluation_row_set_checksum(manifest: FederatedScoreArtifactManifest) -> Checksum:
    return aggregate_score_record_checksum(manifest.evaluation_records, ScoreFrameColumn.STABLE_ROW_ID)


def evaluation_score_order_checksum(manifest: FederatedScoreArtifactManifest) -> Checksum:
    return aggregate_score_record_checksum(
        manifest.evaluation_records,
        ScoreFrameColumn.RECONSTRUCTION_ERROR,
    )


def aggregate_client_checksum(
    clients: tuple[ClientMetricResult, ...],
    field: ClientChecksumField,
) -> Checksum:
    entries = tuple(
        ClientEvidenceChecksum(
            client=item.client,
            checksum=(
                item.evaluation_label_checksum
                if field is ClientChecksumField.EVALUATION_LABEL
                else item.source_row_checksum
            ),
        )
        for item in sorted(clients, key=lambda result: result.client)
    )
    return canonical_checksum(entries)


def aggregate_score_record_checksum(
    records: tuple[FederatedScoreRecord, ...],
    column: ScoreFrameColumn,
) -> Checksum:
    return canonical_checksum(
        tuple(
            ScoreColumnChecksum(
                client=record.scored_client,
                checksum=score_column_checksum(record, column),
            )
            for record in sorted(records, key=lambda item: item.scored_client)
        )
    )


def score_column_checksum(
    record: FederatedScoreRecord,
    column: ScoreFrameColumn,
) -> Checksum:
    values = pl.read_parquet(record.path)[column.value].to_list()
    return ordered_text_checksum(tuple(str(value) for value in values))


def ordered_text_checksum(values: Sequence[str]) -> Checksum:
    digest = sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(
            len(encoded).to_bytes(
                _LENGTH_PREFIX_BYTES,
                byteorder="big",
                signed=False,
            )
        )
        digest.update(encoded)
    return Checksum(digest.hexdigest())
