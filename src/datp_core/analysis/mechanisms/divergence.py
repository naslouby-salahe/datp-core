from enum import StrEnum
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator
from scipy.spatial.distance import jensenshannon

from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, EvidenceRole
from datp_core.core.numeric import MetricValue, PairedObservationCount, PositiveIntegerValue
from datp_core.data.populations.contracts import ClientIdentity

MINIMUM_DIVERGENCE_CLIENTS = PairedObservationCount(2)
DEFAULT_BIN_COUNT = PositiveIntegerValue(64)


class DivergenceBlocker(StrEnum):
    COMMON_SUPPORT_UNRESOLVED = "common_support_unresolved"
    BINNING_UNRESOLVED = "binning_unresolved"
    DENSITY_UNRESOLVED = "density_unresolved"
    SMOOTHING_UNRESOLVED = "smoothing_unresolved"
    ZERO_MASS_UNRESOLVED = "zero_mass_unresolved"
    AGGREGATION_UNRESOLVED = "aggregation_unresolved"
    INSUFFICIENT_CLIENTS = "insufficient_clients"
    EMPTY_SCORE_VECTOR = "empty_score_vector"
    NON_FINITE_SCORE = "non_finite_score"

    @property
    def reason(self) -> AnalysisReasonText:
        return AnalysisReasonText(f"Jensen-Shannon divergence is blocked: {self.value}")


class JensenShannonScoreSource(StrEnum):
    BENIGN_CALIBRATION_SCORES = "benign_calibration_scores"
    BENIGN_EVALUATION_SCORES = "benign_evaluation_scores"


class JensenShannonSharedSupport(StrEnum):
    POOLED_TYPE7_QUANTILES = "pooled_type7_quantiles"


class JensenShannonBinning(StrEnum):
    POOLED_TYPE7_QUANTILE_HISTOGRAM = "pooled_type7_quantile_histogram"


class JensenShannonAggregation(StrEnum):
    MEAN_PAIRWISE = "mean_pairwise"


class JensenShannonLogBase(StrEnum):
    BASE_TWO = "base_2"


class JensenShannonProtocol(StrictModel):
    score_source: JensenShannonScoreSource
    shared_support: JensenShannonSharedSupport
    binning: JensenShannonBinning
    bin_count: PositiveIntegerValue
    logarithm_base: JensenShannonLogBase
    aggregation: JensenShannonAggregation

    @model_validator(mode="after")
    def validate_protocol(self) -> "JensenShannonProtocol":
        if self.bin_count.value < 2:
            raise ValueError("Jensen-Shannon bin count requires at least two bins")
        return self


LOCKED_JENSEN_SHANNON_PROTOCOL = JensenShannonProtocol(
    score_source=JensenShannonScoreSource.BENIGN_CALIBRATION_SCORES,
    shared_support=JensenShannonSharedSupport.POOLED_TYPE7_QUANTILES,
    binning=JensenShannonBinning.POOLED_TYPE7_QUANTILE_HISTOGRAM,
    bin_count=DEFAULT_BIN_COUNT,
    logarithm_base=JensenShannonLogBase.BASE_TWO,
    aggregation=JensenShannonAggregation.MEAN_PAIRWISE,
)


class ClientScoreVector(StrictModel):
    client: ClientIdentity
    scores: tuple[MetricValue, ...]

    @model_validator(mode="after")
    def validate_scores(self) -> "ClientScoreVector":
        if not self.scores:
            raise ValueError("client score vector requires at least one score")
        if any(not np.isfinite(score.value) for score in self.scores):
            raise ValueError("client score vector values must be finite")
        return self


class PairwiseJensenShannonDistance(StrictModel):
    left_client: ClientIdentity
    right_client: ClientIdentity
    value: MetricValue

    @model_validator(mode="after")
    def validate_pair(self) -> "PairwiseJensenShannonDistance":
        if self.left_client >= self.right_client:
            raise ValueError("Jensen-Shannon client pairs must be distinct and sorted")
        return self


class DivergenceResult(StrictModel):
    clients: tuple[ClientIdentity, ...]
    protocol: JensenShannonProtocol
    pairwise_distances: tuple[PairwiseJensenShannonDistance, ...]
    aggregate: MetricValue | None
    blocker: DivergenceBlocker | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "DivergenceResult":
        if len(self.clients) < MINIMUM_DIVERGENCE_CLIENTS.value:
            raise ValueError("divergence analysis requires at least two clients")
        if len(set(self.clients)) != len(self.clients):
            raise ValueError("divergence analysis requires unique clients")
        expected_pairs = len(self.clients) * (len(self.clients) - 1) // 2
        available = self.blocker is None
        if available:
            if len(self.pairwise_distances) != expected_pairs or self.aggregate is None:
                raise ValueError("available divergence requires complete pairwise distances and an aggregate")
            expected_client_pairs = tuple(
                (left_client, right_client)
                for left_index, left_client in enumerate(self.clients)
                for right_client in self.clients[left_index + 1 :]
            )
            actual_client_pairs = tuple(
                (distance.left_client, distance.right_client) for distance in self.pairwise_distances
            )
            if actual_client_pairs != expected_client_pairs:
                raise ValueError("divergence distances must cover each ordered client pair exactly once")
        elif self.pairwise_distances or self.aggregate is not None:
            raise ValueError("blocked divergence cannot contain calculated values")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.blocker is None else AvailabilityStatus.UNAVAILABLE

    @property
    def reason(self) -> AnalysisReasonText | None:
        return None if self.blocker is None else self.blocker.reason


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...],
    blocker: DivergenceBlocker,
    *,
    protocol: JensenShannonProtocol = LOCKED_JENSEN_SHANNON_PROTOCOL,
) -> DivergenceResult:
    ordered = tuple(sorted(clients))
    if len(ordered) < MINIMUM_DIVERGENCE_CLIENTS.value:
        raise ValueError("divergence analysis requires at least two clients")
    return DivergenceResult(
        clients=ordered,
        protocol=protocol,
        pairwise_distances=(),
        aggregate=None,
        blocker=blocker,
    )


def jensen_shannon_divergence(
    vectors: tuple[ClientScoreVector, ...],
    *,
    protocol: JensenShannonProtocol = LOCKED_JENSEN_SHANNON_PROTOCOL,
) -> DivergenceResult:
    if len(vectors) < MINIMUM_DIVERGENCE_CLIENTS.value:
        raise ValueError("Jensen-Shannon divergence requires at least two client score vectors")
    ordered = tuple(sorted(vectors, key=lambda item: item.client))
    clients = tuple(item.client for item in ordered)
    if len(set(clients)) != len(clients):
        raise ValueError("divergence analysis requires unique clients")
    arrays = tuple(_score_array(item.scores) for item in ordered)
    if any(not np.isfinite(array).all() for array in arrays):
        return blocked_jensen_shannon_divergence(
            clients,
            DivergenceBlocker.NON_FINITE_SCORE,
            protocol=protocol,
        )
    edges = np.unique(
        np.quantile(
            np.concatenate(arrays),
            np.linspace(0.0, 1.0, protocol.bin_count.value + 1),
            method="linear",
        )
    )
    if edges.size < 3:
        return blocked_jensen_shannon_divergence(clients, DivergenceBlocker.BINNING_UNRESOLVED, protocol=protocol)
    histograms = tuple(
        _quantile_histogram(array, edges)
        for array in arrays
    )
    pairwise: list[PairwiseJensenShannonDistance] = []
    for left_index, left in enumerate(histograms):
        for right_index, right in enumerate(histograms[left_index + 1 :], start=left_index + 1):
            distance = float(jensenshannon(left, right, base=2.0))
            if not np.isfinite(distance):
                return blocked_jensen_shannon_divergence(
                    clients,
                    DivergenceBlocker.ZERO_MASS_UNRESOLVED,
                    protocol=protocol,
                )
            pairwise.append(
                PairwiseJensenShannonDistance(
                    left_client=clients[left_index],
                    right_client=clients[right_index],
                    value=MetricValue(distance),
                )
            )
    if not pairwise:
        return blocked_jensen_shannon_divergence(
            clients,
            DivergenceBlocker.AGGREGATION_UNRESOLVED,
            protocol=protocol,
        )
    aggregate = MetricValue(float(np.mean([distance.value.value for distance in pairwise])))
    return DivergenceResult(
        clients=clients,
        protocol=protocol,
        pairwise_distances=tuple(pairwise),
        aggregate=aggregate,
        blocker=None,
    )


def _score_array(scores: tuple[MetricValue, ...]) -> NDArray[np.float64]:
    return np.fromiter((score.value for score in scores), dtype=np.float64, count=len(scores))


def _quantile_histogram(
    scores: NDArray[np.float64],
    edges: NDArray[np.float64],
) -> NDArray[np.float64]:
    counts, _ = np.histogram(scores, bins=edges)
    density = counts.astype(np.float64)
    density /= density.sum()
    return density
