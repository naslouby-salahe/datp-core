"""Verification of held-out benign score evidence before threshold diagnostics."""

from dataclasses import dataclass

import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.domain.enums import ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import checksum_file
from datp_core.evaluation.models import HeldOutBenignScore
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.inference import ScoreRecord


@dataclass(frozen=True, slots=True)
class VerifiedHeldOutBenignScores:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    scores: tuple[HeldOutBenignScore, ...]

    def __post_init__(self) -> None:
        if not self.scores:
            raise ScientificContractError("threshold diagnostics require non-empty finite held-out benign scores")
        stable_row_ids = tuple(item.stable_row_id for item in self.scores)
        if len(stable_row_ids) != len(frozenset(stable_row_ids)):
            raise ScientificContractError("threshold diagnostics require unique held-out stable row identities")
        if any(item.client != self.client for item in self.scores):
            raise ScientificContractError("threshold diagnostics require scores from the evaluated client")
        if any(item.score_record.coordinate != self.coordinate for item in self.scores):
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
    """Reject rows not demonstrably present in an unchanged held-out score artifact."""
    by_record: dict[ScoreRecord, list[HeldOutBenignScore]] = {}
    for item in scores:
        by_record.setdefault(item.score_record, []).append(item)
    required = (
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    )
    for record, supplied_rows in by_record.items():
        if not record.path.is_file() or checksum_file(record.path) != record.checksum:
            raise ScientificContractError("threshold diagnostics score provenance is unavailable or changed")
        frame = pl.read_parquet(record.path)
        if any(column not in frame.columns for column in required) or frame.height != record.row_count.value:
            raise ScientificContractError("threshold diagnostics score provenance has an invalid schema or row count")
        stable_row_ids = [item.stable_row_id for item in supplied_rows]
        observed_rows = frame.filter(pl.col(ScoreFrameColumn.STABLE_ROW_ID.value).is_in(stable_row_ids))
        if observed_rows.height != len(supplied_rows):
            raise ScientificContractError(
                "threshold diagnostics score rows are not uniquely proven by their score artifact"
            )
        observed = {
            str(row[ScoreFrameColumn.STABLE_ROW_ID.value]): (
                PopulationOutcomeLabel(str(row[ScoreFrameColumn.OUTCOME_LABEL.value])),
                float(row[ScoreFrameColumn.RECONSTRUCTION_ERROR.value]),
            )
            for row in observed_rows.select(required).iter_rows(named=True)
        }
        if len(observed) != len(supplied_rows):
            raise ScientificContractError(
                "threshold diagnostics score rows are not uniquely proven by their score artifact"
            )
        for item in supplied_rows:
            provenance = observed.get(item.stable_row_id)
            if provenance != (item.outcome_label, item.score.value):
                raise ScientificContractError("threshold diagnostics score row is not proven by its score artifact")
