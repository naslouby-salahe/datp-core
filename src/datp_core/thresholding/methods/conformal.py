"""Finite-sample local conformal threshold construction and contracts."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values import (
    ConformalRankIndex,
    CoverageTarget,
    Quantile,
    Ratio,
    RowCount,
    ScoreValue,
    ThresholdValue,
    floats_absolutely_close,
    floats_exactly_equal,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.splits import FRACTION_TOTAL_ABSOLUTE_TOLERANCE
from datp_core.thresholding.assignments import validate_client_partition
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    conformal_rank_index,
    finite_sample_conformal_threshold,
)


@dataclass(frozen=True, slots=True)
class ConformalAssignment:
    client: ClientIdentity
    calibration_count: RowCount
    rank_index: ConformalRankIndex
    effective_quantile: Quantile
    selected_score: ScoreValue
    tie_count: RowCount
    threshold: ThresholdValue

    def __post_init__(self) -> None:
        require_contract(
            self.rank_index.value <= self.calibration_count.value,
            "conformal rank index must fall within the calibration sample",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            floats_exactly_equal(
                self.threshold.value,
                self.selected_score.value,
            ),
            "conformal threshold value must equal the selected score",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            floats_absolutely_close(
                self.effective_quantile.value,
                self.rank_index.value / self.calibration_count.value,
                FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
            ),
            "conformal effective quantile must equal rank_index / calibration_count",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ConformalThresholdResult:
    coordinate: FederatedTrainingCoordinate
    coverage: CoverageTarget
    eligible_clients: tuple[ClientIdentity, ...]
    assignments: tuple[ConformalAssignment, ...]
    unavailable_clients: tuple[ClientIdentity, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD

    def __post_init__(self) -> None:
        require_contract(
            bool(self.assignments),
            "a conformal threshold result requires at least one assigned client",
            ContractSubject.THRESHOLD,
        )
        validate_client_partition(
            self.eligible_clients,
            tuple(item.client for item in self.assignments),
            self.unavailable_clients,
        )

    @property
    def significance(self) -> Ratio:
        return Ratio(1.0 - self.coverage.value)


def construct_local_conformal_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    quantile: Quantile,
) -> ConformalThresholdResult:
    if not eligible:
        raise ScientificContractError(
            "local conformal construction requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    coverage = CoverageTarget(quantile.value)
    assignments: list[ConformalAssignment] = []
    unavailable: list[ClientIdentity] = []
    for client_scores in sorted(eligible, key=lambda item: item.client):
        calibration_count = RowCount(int(client_scores.as_array.size))
        rank_index = conformal_rank_index(calibration_count, coverage)
        if rank_index.value > calibration_count.value:
            unavailable.append(client_scores.client)
            continue
        threshold, _, effective_quantile, tie_count = finite_sample_conformal_threshold(
            client_scores.as_array,
            coverage,
        )
        assignments.append(
            ConformalAssignment(
                client=client_scores.client,
                calibration_count=calibration_count,
                rank_index=rank_index,
                effective_quantile=effective_quantile,
                selected_score=ScoreValue(threshold.value),
                tie_count=tie_count,
                threshold=threshold,
            )
        )
    if not assignments:
        raise ScientificContractError(
            "no eligible client has sufficient support for the finite-sample conformal rule",
            subject=ContractSubject.CALIBRATION,
        )
    return ConformalThresholdResult(
        coordinate=eligible[0].coordinate,
        coverage=coverage,
        eligible_clients=tuple(item.client for item in eligible),
        assignments=tuple(assignments),
        unavailable_clients=tuple(unavailable),
    )
