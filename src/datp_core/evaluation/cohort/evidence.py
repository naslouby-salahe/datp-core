"""Derivation of threshold-independent cohort support counts from score artifacts."""

import polars as pl

from datp_core.datasets.partitioning.contracts import (
    ClientIdentity,
    ClientPartitionCounts,
    PopulationOutcomeLabel,
)
from datp_core.domain.enums import ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import RowCount
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.inference import ScoreArtifactManifest, ScoreRecord

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]


def client_partition_counts_from_scores(
    manifest: FederatedScoreArtifactManifest,
) -> tuple[ClientPartitionCounts, ...]:
    calibration = tuple(sorted(manifest.calibration_records, key=lambda record: record.scored_client))
    evaluation = tuple(sorted(manifest.evaluation_records, key=lambda record: record.scored_client))
    if tuple(record.scored_client for record in calibration) != tuple(record.scored_client for record in evaluation):
        raise ScientificContractError("evaluation inputs require matching calibration and evaluation score clients")
    return tuple(
        ClientPartitionCounts(
            client=calibration_record.scored_client,
            benign_calibration_count=_label_count(calibration_record, PopulationOutcomeLabel.BENIGN),
            benign_evaluation_count=_label_count(evaluation_record, PopulationOutcomeLabel.BENIGN),
            attack_evaluation_count=_label_count(evaluation_record, PopulationOutcomeLabel.ATTACK),
            accepted=True,
            deployment_fallback=False,
        )
        for calibration_record, evaluation_record in zip(calibration, evaluation, strict=True)
    )


def _label_count(record: FederatedScoreRecord, label: PopulationOutcomeLabel) -> RowCount:
    frame = pl.read_parquet(record.path)
    return RowCount(int((frame[ScoreFrameColumn.OUTCOME_LABEL.value] == label.value).sum()))
