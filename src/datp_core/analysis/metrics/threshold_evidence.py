from collections import defaultdict
from dataclasses import dataclass

import polars as pl

from datp_core.analysis.metrics.models import FederatedScoreRecord, HeldOutBenignScore
from datp_core.artifacts.provenance import checksum_file
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ScoreFrameColumn
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.training.models import FederatedTrainingCoordinate


@dataclass(frozen=True, slots=True)
class VerifiedHeldOutBenignScores:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    scores: tuple[HeldOutBenignScore, ...]

    def __post_init__(self) -> None:
        if not self.scores:
            raise ScientificContractError("threshold diagnostics require non-empty finite held-out benign scores")
        stable_row_ids = tuple(item.stable_row_id for item in self.scores)
        if len(stable_row_ids) != len(set(stable_row_ids)):
            raise ScientificContractError("threshold diagnostics require unique held-out stable row identities")

        for item in self.scores:
            if item.client != self.client:
                raise ScientificContractError("threshold diagnostics require scores from the evaluated client")
            if item.score_record.coordinate != self.coordinate:
                raise ScientificContractError(
                    "threshold diagnostics require score provenance matching the evaluation coordinate"
                )


def verify_held_out_benign_scores(
    *,
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    scores: tuple[HeldOutBenignScore, ...],
) -> VerifiedHeldOutBenignScores:
    verified = VerifiedHeldOutBenignScores(client=client, coordinate=coordinate, scores=scores)
    _verify_score_rows(verified.scores)
    return verified


def _verify_score_rows(scores: tuple[HeldOutBenignScore, ...]) -> None:
    by_record: defaultdict[FederatedScoreRecord, list[HeldOutBenignScore]] = defaultdict(list)
    for item in scores:
        by_record[item.score_record].append(item)

    required = (
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    )
    required_set = set(required)

    for record, supplied_rows in by_record.items():
        if not record.path.is_file() or checksum_file(record.path) != record.checksum:
            raise ScientificContractError("threshold diagnostics score provenance is unavailable or changed")

        frame = pl.read_parquet(record.path)
        if not required_set.issubset(frame.columns) or frame.height != record.row_count.value:
            raise ScientificContractError("threshold diagnostics score provenance has an invalid schema or row count")

        stable_row_ids = [item.stable_row_id for item in supplied_rows]
        observed_rows = frame.filter(pl.col(ScoreFrameColumn.STABLE_ROW_ID.value).is_in(stable_row_ids))

        if observed_rows.height != len(supplied_rows):
            raise ScientificContractError(
                "threshold diagnostics score rows are not uniquely proven by their score artifact"
            )

        observed = {
            str(row[0]): (
                PopulationOutcomeLabel(str(row[1])),
                float(row[2]),
            )
            for row in observed_rows.select(required).iter_rows()
        }

        if len(observed) != len(supplied_rows):
            raise ScientificContractError(
                "threshold diagnostics score rows are not uniquely proven by their score artifact"
            )

        for item in supplied_rows:
            provenance = observed.get(item.stable_row_id)
            if provenance != (item.outcome_label, item.score.value):
                raise ScientificContractError("threshold diagnostics score row is not proven by its score artifact")
