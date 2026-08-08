"""Locked Jensen–Shannon divergence estimator for client score heterogeneity."""

from enum import StrEnum
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator
from scipy.spatial.distance import jensenshannon

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole
from datp_core.core.numeric import MetricValue, PairedObservationCount, PositiveIntegerValue
from datp_core.data.populations.contracts import ClientIdentity

MINIMUM_DIVERGENCE_CLIENTS = PairedObservationCount(2)
DEFAULT_BIN_COUNT = PositiveIntegerValue(32)
DEFAULT_SMOOTHING = MetricValue(1e-12)


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
    def reason(self) -> str:
        return f"Jensen-Shannon divergence is blocked: {self.value}"


class JensenShannonScoreSource(StrEnum):
    BENIGN_CALIBRATION_SCORES = "benign_calibration_scores"
    BENIGN_EVALUATION_SCORES = "benign_evaluation_scores"


class JensenShannonSharedSupport(StrEnum):
    GLOBAL_MIN_MAX = "global_min_max"


class JensenShannonBinning(StrEnum):
    EQUAL_WIDTH_HISTOGRAM = "equal_width_histogram"


class JensenShannonAggregation(StrEnum):
    MEAN_PAIRWISE = "mean_pairwise"


class JensenShannonLogBase(StrEnum):
    BASE_TWO = "base_2"


class JensenShannonProtocol(StrictModel):
    score_source: JensenShannonScoreSource
    shared_support: JensenShannonSharedSupport
    binning: JensenShannonBinning
    bin_count: PositiveIntegerValue
    smoothing_constant: MetricValue
    logarithm_base: JensenShannonLogBase
    aggregation: JensenShannonAggregation

    @model_validator(mode="after")
    def validate_protocol(self) -> "JensenShannonProtocol":
        if self.bin_count.value < 2:
            raise ValueError("Jensen-Shannon bin count requires at least two bins")
        if self.smoothing_constant.value <= 0.0:
            raise ValueError("Jensen-Shannon smoothing constant must be positive")
        return self


LOCKED_JENSEN_SHANNON_PROTOCOL = JensenShannonProtocol(
    score_source=JensenShannonScoreSource.BENIGN_CALIBRATION_SCORES,
    shared_support=JensenShannonSharedSupport.GLOBAL_MIN_MAX,
    binning=JensenShannonBinning.EQUAL_WIDTH_HISTOGRAM,
    bin_count=DEFAULT_BIN_COUNT,
    smoothing_constant=DEFAULT_SMOOTHING,
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


class DivergenceResult(StrictModel):
    clients: tuple[ClientIdentity, ...]
    protocol: JensenShannonProtocol
    source_score_checksum: Checksum | None
    pairwise_values: tuple[MetricValue, ...]
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
            if len(self.pairwise_values) != expected_pairs or self.aggregate is None:
                raise ValueError("available divergence requires complete pairwise values and an aggregate")
            if self.source_score_checksum is None:
                raise ValueError("available divergence requires a source-score checksum")
        elif self.pairwise_values or self.aggregate is not None:
            raise ValueError("blocked divergence cannot contain calculated values")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.blocker is None else AvailabilityStatus.UNAVAILABLE

    @property
    def reason(self) -> str | None:
        return None if self.blocker is None else self.blocker.reason


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...],
    blocker: DivergenceBlocker,
    *,
    protocol: JensenShannonProtocol = LOCKED_JENSEN_SHANNON_PROTOCOL,
    source_score_checksum: Checksum | None = None,
) -> DivergenceResult:
    ordered = tuple(sorted(clients))
    if len(ordered) < MINIMUM_DIVERGENCE_CLIENTS.value:
        raise ValueError("divergence analysis requires at least two clients")
    return DivergenceResult(
        clients=ordered,
        protocol=protocol,
        source_score_checksum=source_score_checksum,
        pairwise_values=(),
        aggregate=None,
        blocker=blocker,
    )


def jensen_shannon_divergence(
    vectors: tuple[ClientScoreVector, ...],
    *,
    protocol: JensenShannonProtocol = LOCKED_JENSEN_SHANNON_PROTOCOL,
    source_score_checksum: Checksum,
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
            source_score_checksum=source_score_checksum,
        )
    support_min = float(min(float(array.min()) for array in arrays))
    support_max = float(max(float(array.max()) for array in arrays))
    if not np.isfinite(support_min) or not np.isfinite(support_max):
        return blocked_jensen_shannon_divergence(
            clients,
            DivergenceBlocker.COMMON_SUPPORT_UNRESOLVED,
            protocol=protocol,
            source_score_checksum=source_score_checksum,
        )
    if support_max <= support_min:
        support_max = support_min + protocol.smoothing_constant.value
    histograms = tuple(
        _smoothed_histogram(
            array,
            support_min=support_min,
            support_max=support_max,
            bin_count=protocol.bin_count.value,
            smoothing=protocol.smoothing_constant.value,
        )
        for array in arrays
    )
    pairwise: list[MetricValue] = []
    for left_index, left in enumerate(histograms):
        for right in histograms[left_index + 1 :]:
            distance = float(jensenshannon(left, right, base=2.0))
            if not np.isfinite(distance):
                return blocked_jensen_shannon_divergence(
                    clients,
                    DivergenceBlocker.ZERO_MASS_UNRESOLVED,
                    protocol=protocol,
                    source_score_checksum=source_score_checksum,
                )
            pairwise.append(MetricValue(distance))
    if not pairwise:
        return blocked_jensen_shannon_divergence(
            clients,
            DivergenceBlocker.AGGREGATION_UNRESOLVED,
            protocol=protocol,
            source_score_checksum=source_score_checksum,
        )
    aggregate = MetricValue(float(np.mean([value.value for value in pairwise])))
    return DivergenceResult(
        clients=clients,
        protocol=protocol,
        source_score_checksum=source_score_checksum,
        pairwise_values=tuple(pairwise),
        aggregate=aggregate,
        blocker=None,
    )


def _score_array(scores: tuple[MetricValue, ...]) -> NDArray[np.float64]:
    return np.fromiter((score.value for score in scores), dtype=np.float64, count=len(scores))


def _smoothed_histogram(
    scores: NDArray[np.float64],
    *,
    support_min: float,
    support_max: float,
    bin_count: int,
    smoothing: float,
) -> NDArray[np.float64]:
    counts, _ = np.histogram(scores, bins=bin_count, range=(support_min, support_max))
    density = counts.astype(np.float64) + smoothing
    density /= density.sum()
    return density
