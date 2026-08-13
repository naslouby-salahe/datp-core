from collections import defaultdict

import numpy as np
from pydantic import model_validator

from datp_core.analysis.mechanisms.policy_surface import (
    PolicySurfaceCell,
    PolicySurfacePolicyMetric,
    policy_surface_cell,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import CalibrationSupportLevel, FederatedThresholdMethod, RegimeLabel
from datp_core.core.numeric import CalibrationSize, MetricValue, ReplicateIndex, Seed

_FINITE_SUPPORT = (
    CalibrationSupportLevel.M50,
    CalibrationSupportLevel.M100,
    CalibrationSupportLevel.M500,
)
_SUPPORT_VALUE = {
    CalibrationSupportLevel.M50: 50,
    CalibrationSupportLevel.M100: 100,
    CalibrationSupportLevel.M500: 500,
}


class SupportInteractionObservation(StrictModel):
    seed: Seed
    alpha_label: RegimeLabel
    support: CalibrationSupportLevel
    replicate: ReplicateIndex | None
    heterogeneity: MetricValue
    policy_metrics: tuple[PolicySurfacePolicyMetric, ...]

    @model_validator(mode="after")
    def validate_support_replicate(self) -> "SupportInteractionObservation":
        if self.support is CalibrationSupportLevel.FULL:
            if self.replicate is not None:
                raise ValueError("full support has no nested replicate")
        elif self.replicate is None:
            raise ValueError("finite support requires a nested replicate")
        return self


class SupportInteractionCoefficient(StrictModel):
    seed: Seed
    intercept: MetricValue
    heterogeneity: MetricValue
    log10_support: MetricValue
    heterogeneity_log10_support: MetricValue


class SupportInteractionAnalysis(StrictModel):
    observations: tuple[SupportInteractionObservation, ...]
    coefficients: tuple[SupportInteractionCoefficient, ...]
    policy_surface: tuple[PolicySurfaceCell, ...]


def summarize_support_interaction(
    observations: tuple[SupportInteractionObservation, ...],
) -> SupportInteractionAnalysis:
    """Summarize the locked interaction grid without treating nested replicates as seeds."""

    _validate_observations(observations)
    grouped: dict[tuple[Seed, RegimeLabel, CalibrationSupportLevel], list[SupportInteractionObservation]] = defaultdict(
        list
    )
    for observation in observations:
        grouped[(observation.seed, observation.alpha_label, observation.support)].append(observation)

    surface = tuple(
        _surface_cell(seed, alpha, support, values)
        for (seed, alpha, support), values in sorted(
            grouped.items(),
            key=lambda item: (item[0][0].value, str(item[0][1]), item[0][2].value),
        )
    )
    coefficients = tuple(
        _seed_coefficient(seed, grouped)
        for seed in sorted(frozenset(item.seed for item in observations), key=lambda item: item.value)
    )
    return SupportInteractionAnalysis(observations=observations, coefficients=coefficients, policy_surface=surface)


def _validate_observations(observations: tuple[SupportInteractionObservation, ...]) -> None:
    if not observations:
        raise ValueError("support interaction requires observations")
    identities = tuple((item.seed, item.alpha_label, item.support, item.replicate) for item in observations)
    if len(identities) != len(frozenset(identities)):
        raise ValueError("support interaction observations must be unique by seed, alpha, support, and replicate")
    expected_policies = frozenset(item.policy for item in observations[0].policy_metrics)
    if not expected_policies:
        raise ValueError("support interaction observations require policy metrics")
    if any(
        frozenset(item.policy for item in observation.policy_metrics) != expected_policies
        for observation in observations
    ):
        raise ValueError("support interaction policy sets must be identical across cells")


def _surface_cell(
    seed: Seed,
    alpha: RegimeLabel,
    support: CalibrationSupportLevel,
    observations: list[SupportInteractionObservation],
) -> PolicySurfaceCell:
    heterogeneity = observations[0].heterogeneity
    if any(item.heterogeneity != heterogeneity for item in observations):
        raise ValueError("heterogeneity must be fixed across nested support replicates")
    policies = tuple(
        PolicySurfacePolicyMetric(
            policy=policy,
            cv_fpr=_mean_metric(tuple(_metric_for(item, policy).cv_fpr for item in observations)),
            p10_macro_f1=_mean_metric(tuple(_metric_for(item, policy).p10_macro_f1 for item in observations)),
            worst_client_balanced_accuracy=_mean_metric(
                tuple(_metric_for(item, policy).worst_client_balanced_accuracy for item in observations)
            ),
        )
        for policy in sorted((item.policy for item in observations[0].policy_metrics), key=lambda item: item.value)
    )
    calibration_size = None if support is CalibrationSupportLevel.FULL else _support_size(support)
    return policy_surface_cell(
        seed=seed,
        alpha_label=str(alpha),
        calibration_size=calibration_size,
        heterogeneity=heterogeneity,
        policies=policies,
    )


def _seed_coefficient(
    seed: Seed,
    grouped: dict[tuple[Seed, RegimeLabel, CalibrationSupportLevel], list[SupportInteractionObservation]],
) -> SupportInteractionCoefficient:
    finite = tuple(
        (alpha, support, values)
        for (candidate_seed, alpha, support), values in grouped.items()
        if candidate_seed == seed and support in _FINITE_SUPPORT
    )
    alpha_labels = frozenset(alpha for alpha, _, _ in finite)
    if len(finite) != len(alpha_labels) * len(_FINITE_SUPPORT) or len(alpha_labels) != 3:
        raise ValueError("each seed requires the complete nine-cell finite interaction grid")
    design: list[tuple[float, float, float, float]] = []
    outcomes: list[float] = []
    for _alpha, support, values in sorted(finite, key=lambda item: (str(item[0]), item[1].value)):
        shared = _mean_metric(
            tuple(_metric_for(item, FederatedThresholdMethod.SHARED_THRESHOLD).cv_fpr for item in values)
        )
        local = _mean_metric(
            tuple(_metric_for(item, FederatedThresholdMethod.LOCAL_THRESHOLD).cv_fpr for item in values)
        )
        if shared is None or local is None:
            raise ValueError("interaction coefficients require available shared and local CV(FPR)")
        heterogeneity = values[0].heterogeneity.value
        log_support = float(np.log10(_SUPPORT_VALUE[support] / 100.0))
        design.append((1.0, heterogeneity, log_support, heterogeneity * log_support))
        outcomes.append(shared.value - local.value)
    coefficient, _, rank, _ = np.linalg.lstsq(np.asarray(design, dtype=np.float64), np.asarray(outcomes), rcond=None)
    if rank != 4:
        raise ValueError("locked interaction design is rank deficient")
    return SupportInteractionCoefficient(
        seed=seed,
        intercept=MetricValue(float(coefficient[0])),
        heterogeneity=MetricValue(float(coefficient[1])),
        log10_support=MetricValue(float(coefficient[2])),
        heterogeneity_log10_support=MetricValue(float(coefficient[3])),
    )


def _metric_for(
    observation: SupportInteractionObservation,
    policy: FederatedThresholdMethod,
) -> PolicySurfacePolicyMetric:
    matches = tuple(item for item in observation.policy_metrics if item.policy is policy)
    if len(matches) != 1:
        raise ValueError("support interaction policy metrics must resolve exactly once")
    return matches[0]


def _mean_metric(values: tuple[MetricValue | None, ...]) -> MetricValue | None:
    if any(item is None for item in values):
        return None
    return MetricValue(float(np.mean(tuple(item.value for item in values if item is not None), dtype=np.float64)))


def _support_size(support: CalibrationSupportLevel) -> CalibrationSize:
    return CalibrationSize(_SUPPORT_VALUE[support])
