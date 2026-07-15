from dataclasses import dataclass
from math import fsum

from datp_core.application.ports.thresholding import AssignThresholdRequest, ThresholdStrategy
from datp_core.domain.errors import ThresholdError
from datp_core.domain.mathematics.dispersion import ClientMoment
from datp_core.domain.thresholding.federated_statistics import (
    FedStatsBenignThresholdSpec,
    FedStatsCandidateExceedance,
    ThresholdComparatorRole,
)
from datp_core.domain.thresholding.policies import ThresholdAssignment, ThresholdValue
from datp_core.infrastructure.thresholding.policies import (
    assignment_from_values,
    require_assignment_subject,
    roster_clients,
    unexpected_construction,
)
from datp_core.infrastructure.thresholding.quantiles import CalibrationScoreReader


@dataclass(frozen=True, slots=True, kw_only=True)
class FedStatsThresholdStrategy(ThresholdStrategy):
    reader: CalibrationScoreReader

    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment:
        specification = request.construction
        if type(specification) is not FedStatsBenignThresholdSpec:
            raise unexpected_construction(request)
        require_assignment_subject(request=request, expected=ThresholdComparatorRole.FED_STATS_BENIGN)
        scores = self._scores(request)
        value = _selected_threshold_value(request=request, specification=specification, scores=scores)
        return assignment_from_values(request=request, values=tuple(value for _ in scores))

    def _scores(self, request: AssignThresholdRequest) -> tuple[tuple[float, ...], ...]:
        return tuple(
            self.reader.read(calibration_scores=request.calibration_scores, client_index=index)
            for index, _ in enumerate(roster_clients(request))
        )


def _selected_threshold_value(
    *,
    request: AssignThresholdRequest,
    specification: FedStatsBenignThresholdSpec,
    scores: tuple[tuple[float, ...], ...],
) -> ThresholdValue:
    moments = tuple(_client_moment(values) for values in scores)
    pooled = specification.pooled_evidence(client_moments=moments)
    candidates = tuple(
        FedStatsCandidateExceedance(
            multiplier=multiplier,
            benign_exceedance_count=sum(
                score > pooled.global_mean + float(multiplier.value) * pooled.global_variance**0.5
                for client_scores in scores
                for score in client_scores
            ),
        )
        for multiplier in specification.candidate_grid
    )
    selected = specification.select_matched_exceedance(
        pooled_evidence=pooled,
        candidate_exceedances=candidates,
        target_exceedance_rate=request.assignment_metadata.fpr_target,
    )
    return ThresholdValue(value=selected.threshold.value)


def _client_moment(values: tuple[float, ...]) -> ClientMoment:
    if not values:
        raise ThresholdError(
            detail="FedStats requires at least one benign calibration score per client",
            policy="fed_stats_benign",
            missing_field="benign calibration scores",
        )
    mean = fsum(values) / len(values)
    variance = fsum((value - mean) ** 2 for value in values) / len(values)
    return ClientMoment(sample_count=len(values), mean=mean, variance=variance)
