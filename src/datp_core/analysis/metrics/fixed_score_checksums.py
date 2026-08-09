from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from datp_core.analysis.metrics.models import ClientMetricResult
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.identifiers import ScoreFrameColumn, StableRowId
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreRecord
from datp_core.detector.training.models import FederatedTrainingCoordinate

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]


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
    return Checksum.from_ordered_texts(tuple(label.value for label in labels))


def source_row_checksum(rows: Sequence[StableRowId]) -> Checksum:
    return Checksum.from_ordered_texts(tuple(rows))


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
    is_label_field = field is ClientChecksumField.EVALUATION_LABEL
    entries = tuple(
        ClientEvidenceChecksum(
            client=item.client,
            checksum=item.evaluation_label_checksum if is_label_field else item.source_row_checksum,
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
    data = pl.read_parquet(record.path, columns=[column.value]).to_dict(as_series=False)
    return Checksum.from_ordered_texts(tuple(str(value) for value in data[column.value]))
