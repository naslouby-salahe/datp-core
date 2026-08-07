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
    calibration = sorted(manifest.calibration_records, key=lambda record: record.scored_client)
    evaluation = sorted(manifest.evaluation_records, key=lambda record: record.scored_client)

    if len(calibration) != len(evaluation):
        raise ScientificContractError("evaluation inputs require matching calibration and evaluation score clients")

    counts: list[ClientPartitionCounts] = []
    for calibration_record, evaluation_record in zip(calibration, evaluation, strict=True):
        if calibration_record.scored_client != evaluation_record.scored_client:
            raise ScientificContractError("evaluation inputs require matching calibration and evaluation score clients")

        (benign_cal,) = _extract_label_counts(calibration_record, (PopulationOutcomeLabel.BENIGN,))
        benign_eval, attack_eval = _extract_label_counts(
            evaluation_record, (PopulationOutcomeLabel.BENIGN, PopulationOutcomeLabel.ATTACK)
        )

        counts.append(
            ClientPartitionCounts(
                client=calibration_record.scored_client,
                benign_calibration_count=benign_cal,
                benign_evaluation_count=benign_eval,
                attack_evaluation_count=attack_eval,
                accepted=True,
                deployment_fallback=False,
            )
        )

    return tuple(counts)


def _extract_label_counts(
    record: FederatedScoreRecord, labels: tuple[PopulationOutcomeLabel, ...]
) -> tuple[RowCount, ...]:
    col_name = ScoreFrameColumn.OUTCOME_LABEL.value
    exprs = [pl.col(col_name).eq(label.value).sum().alias(label.name) for label in labels]

    result = pl.scan_parquet(record.path).select(exprs).collect().row(0)

    return tuple(RowCount(count) for count in result)
