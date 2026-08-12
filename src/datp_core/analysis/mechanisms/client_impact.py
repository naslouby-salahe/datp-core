from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.mechanisms.movement import ThresholdMovement, ThresholdMovementCohort
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, ExperimentId
from datp_core.core.numeric import ClientCount, MetricValue, PairedObservationCount, Ratio, Seed, SeedObservationCount
from datp_core.data.populations.contracts import ClientIdentity


class ParetoClientImpact(StrEnum):
    PARETO_IMPROVED = "pareto_improved"
    PARETO_HARMED = "pareto_harmed"
    TRADEOFF_FPR_BETTER_TPR_WORSE = "tradeoff_fpr_better_tpr_worse"
    TRADEOFF_FPR_WORSE_TPR_BETTER = "tradeoff_fpr_worse_tpr_better"
    NO_FPR_CHANGE = "no_fpr_change"


class ClientImpactFraction(StrictModel):
    numerator: PairedObservationCount | None
    denominator: ClientCount | None
    value: Ratio | None
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_availability(self) -> ClientImpactFraction:
        available = self.numerator is not None or self.denominator is not None or self.value is not None
        if available:
            if self.numerator is None or self.denominator is None or self.value is None or self.reason is not None:
                raise ValueError("available client-impact fraction requires numerator, denominator, and value only")
            if self.numerator.value > self.denominator.value:
                raise ValueError("client-impact fraction numerator cannot exceed denominator")
            if self.value.value != self.numerator.value / self.denominator.value:
                raise ValueError("client-impact fraction must equal its persisted integer ratio")
        elif self.reason is None:
            raise ValueError("unavailable client-impact fraction requires a reason")
        return self


class ParetoClientImpactFractions(StrictModel):
    pareto_improved: ClientImpactFraction
    pareto_harmed: ClientImpactFraction
    tradeoff_fpr_better_tpr_worse: ClientImpactFraction
    tradeoff_fpr_worse_tpr_better: ClientImpactFraction
    no_fpr_change: ClientImpactFraction

    @model_validator(mode="after")
    def validate_common_attack_cohort(self) -> ParetoClientImpactFractions:
        fractions = (
            self.pareto_improved,
            self.pareto_harmed,
            self.tradeoff_fpr_better_tpr_worse,
            self.tradeoff_fpr_worse_tpr_better,
            self.no_fpr_change,
        )
        denominators = {item.denominator for item in fractions}
        if None in denominators:
            if denominators != {None}:
                raise ValueError("Pareto fractions must be jointly available or unavailable")
            return self
        if len(denominators) != 1:
            raise ValueError("Pareto fractions require one common attack-evaluable denominator")
        if sum(item.numerator.value for item in fractions if item.numerator is not None) != next(
            item.denominator.value for item in fractions if item.denominator is not None
        ):
            raise ValueError("Pareto category numerators must partition the common attack-evaluable cohort")
        return self


class ClientImpactSeedSummary(StrictModel):
    seed: Seed
    experiment: ExperimentId
    fpr_helped: ClientImpactFraction
    fpr_harmed: ClientImpactFraction
    fpr_unchanged: ClientImpactFraction
    tpr_loss: ClientImpactFraction
    macro_f1_loss: ClientImpactFraction
    balanced_accuracy_loss: ClientImpactFraction
    fpr_harm_magnitude: ClientImpactMagnitudeSummary
    tpr_loss_magnitude: ClientImpactMagnitudeSummary
    pareto: ParetoClientImpactFractions
    availability: AvailabilityStatus
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_seed_summary(self) -> ClientImpactSeedSummary:
        if self.availability is AvailabilityStatus.AVAILABLE:
            if self.reason is not None or self.fpr_helped.value is None:
                raise ValueError("available client-impact summary requires FPR fractions and no reason")
        elif self.reason is None:
            raise ValueError("unavailable client-impact summary requires a reason")
        return self


class ClientImpactMagnitudeSummary(StrictModel):
    median: MetricValue | None
    maximum: MetricValue | None
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_availability(self) -> ClientImpactMagnitudeSummary:
        available = self.median is not None or self.maximum is not None
        if available:
            if self.median is None or self.maximum is None or self.reason is not None:
                raise ValueError("available harm-magnitude summary requires median and maximum only")
        elif self.reason is None:
            raise ValueError("unavailable harm-magnitude summary requires a reason")
        return self


class ClientImpactFractionSummary(StrictModel):
    seed_values: tuple[ClientImpactFraction, ...]
    valid_seed_count: SeedObservationCount
    unavailable_seed_count: SeedObservationCount
    arithmetic_mean: MetricValue | None
    median: MetricValue | None
    minimum: MetricValue | None
    maximum: MetricValue | None

    @model_validator(mode="after")
    def validate_summary(self) -> ClientImpactFractionSummary:
        if self.valid_seed_count.value + self.unavailable_seed_count.value != len(self.seed_values):
            raise ValueError("client-impact summary counts must partition its seed values")
        statistics = (self.arithmetic_mean, self.median, self.minimum, self.maximum)
        if self.valid_seed_count.value == 0:
            if any(value is not None for value in statistics):
                raise ValueError("unavailable client-impact summaries cannot fabricate statistics")
        elif any(value is None for value in statistics):
            raise ValueError("available client-impact summaries require all locked descriptive statistics")
        return self


class ClientImpactCampaignSummary(StrictModel):
    seed_summaries: tuple[ClientImpactSeedSummary, ...]
    device_frequencies: tuple[ClientImpactDeviceFrequency, ...]
    fpr_helped: ClientImpactFractionSummary
    fpr_harmed: ClientImpactFractionSummary
    fpr_unchanged: ClientImpactFractionSummary
    tpr_loss: ClientImpactFractionSummary
    macro_f1_loss: ClientImpactFractionSummary
    balanced_accuracy_loss: ClientImpactFractionSummary
    pareto_improved: ClientImpactFractionSummary
    pareto_harmed: ClientImpactFractionSummary
    tradeoff_fpr_better_tpr_worse: ClientImpactFractionSummary
    tradeoff_fpr_worse_tpr_better: ClientImpactFractionSummary
    no_fpr_change: ClientImpactFractionSummary

    @model_validator(mode="after")
    def validate_campaign(self) -> ClientImpactCampaignSummary:
        seeds = tuple(item.seed for item in self.seed_summaries)
        if not seeds:
            raise ValueError("client-impact campaign summary requires seed evidence")
        if len(seeds) != len(frozenset(seeds)):
            raise ValueError("client-impact campaign seed evidence must be unique")
        return self


class ClientImpactDeviceFrequency(StrictModel):
    client: ClientIdentity
    observed_seed_count: SeedObservationCount
    fpr_help_frequency: ClientImpactFraction
    fpr_harm_frequency: ClientImpactFraction
    tpr_loss_frequency: ClientImpactFraction

    @model_validator(mode="after")
    def validate_device_frequency(self) -> ClientImpactDeviceFrequency:
        if self.observed_seed_count.value == 0:
            raise ValueError("client-impact device frequency requires observed seed evidence")
        for fraction in (self.fpr_help_frequency, self.fpr_harm_frequency):
            if fraction.denominator is None or fraction.denominator.value != self.observed_seed_count.value:
                raise ValueError("FPR device frequencies must use every observed seed")
        return self


def summarize_client_impact(cohort: ThresholdMovementCohort) -> ClientImpactSeedSummary:
    if cohort.availability is not AvailabilityStatus.AVAILABLE or not cohort.movements:
        reason = cohort.reason or AnalysisReasonText("no threshold-movement observations")
        unavailable = _unavailable_fraction(reason)
        return ClientImpactSeedSummary(
            seed=Seed(0),
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            fpr_helped=unavailable,
            fpr_harmed=unavailable,
            fpr_unchanged=unavailable,
            tpr_loss=unavailable,
            macro_f1_loss=unavailable,
            balanced_accuracy_loss=unavailable,
            fpr_harm_magnitude=_unavailable_magnitude(reason),
            tpr_loss_magnitude=_unavailable_magnitude(reason),
            pareto=ParetoClientImpactFractions(
                pareto_improved=unavailable,
                pareto_harmed=unavailable,
                tradeoff_fpr_better_tpr_worse=unavailable,
                tradeoff_fpr_worse_tpr_better=unavailable,
                no_fpr_change=unavailable,
            ),
            availability=AvailabilityStatus.UNAVAILABLE,
            reason=reason,
        )
    movements = cohort.movements
    first = movements[0]
    if any(item.seed != first.seed or item.experiment is not first.experiment for item in movements[1:]):
        raise ValueError("client-impact summary requires one seed and experiment")
    fpr_relief = tuple(-item.delta_fpr.value for item in movements)
    fpr_helped = _fraction(sum(value > 0.0 for value in fpr_relief), len(fpr_relief))
    fpr_harmed = _fraction(sum(value < 0.0 for value in fpr_relief), len(fpr_relief))
    fpr_unchanged = _fraction(sum(value == 0.0 for value in fpr_relief), len(fpr_relief))
    attack_movements = tuple(item for item in movements if item.delta_tpr is not None)
    if not attack_movements:
        unavailable = _unavailable_fraction(AnalysisReasonText("no common FPR/TPR-evaluable clients"))
        return ClientImpactSeedSummary(
            seed=first.seed,
            experiment=first.experiment,
            fpr_helped=fpr_helped,
            fpr_harmed=fpr_harmed,
            fpr_unchanged=fpr_unchanged,
            tpr_loss=unavailable,
            macro_f1_loss=unavailable,
            balanced_accuracy_loss=unavailable,
            fpr_harm_magnitude=_magnitude_summary(
                tuple(-value for value in fpr_relief if value < 0.0), "no FPR-harmed clients"
            ),
            tpr_loss_magnitude=_unavailable_magnitude(AnalysisReasonText("no common FPR/TPR-evaluable clients")),
            pareto=ParetoClientImpactFractions(
                pareto_improved=unavailable,
                pareto_harmed=unavailable,
                tradeoff_fpr_better_tpr_worse=unavailable,
                tradeoff_fpr_worse_tpr_better=unavailable,
                no_fpr_change=unavailable,
            ),
            availability=AvailabilityStatus.AVAILABLE,
            reason=None,
        )
    tpr_changes = tuple(item.delta_tpr.value for item in attack_movements if item.delta_tpr is not None)
    macro_f1_changes = tuple(item.delta_macro_f1.value for item in attack_movements if item.delta_macro_f1 is not None)
    ba_changes = tuple(
        item.delta_balanced_accuracy.value for item in attack_movements if item.delta_balanced_accuracy is not None
    )
    pareto_counts = {category: 0 for category in ParetoClientImpact}
    for item in attack_movements:
        if item.delta_tpr is None:
            raise ValueError("attack client must retain a TPR change")
        category = _pareto_category(-item.delta_fpr.value, item.delta_tpr.value)
        pareto_counts[category] += 1
    return ClientImpactSeedSummary(
        seed=first.seed,
        experiment=first.experiment,
        fpr_helped=fpr_helped,
        fpr_harmed=fpr_harmed,
        fpr_unchanged=fpr_unchanged,
        tpr_loss=_fraction(sum(value < 0.0 for value in tpr_changes), len(tpr_changes)),
        macro_f1_loss=_loss_fraction(macro_f1_changes, "no common FPR/Macro-F1-evaluable clients"),
        balanced_accuracy_loss=_loss_fraction(ba_changes, "no common FPR/balanced-accuracy-evaluable clients"),
        fpr_harm_magnitude=_magnitude_summary(
            tuple(-value for value in fpr_relief if value < 0.0), "no FPR-harmed clients"
        ),
        tpr_loss_magnitude=_magnitude_summary(
            tuple(-value for value in tpr_changes if value < 0.0), "no TPR-loss clients"
        ),
        pareto=ParetoClientImpactFractions(
            pareto_improved=_fraction(pareto_counts[ParetoClientImpact.PARETO_IMPROVED], len(attack_movements)),
            pareto_harmed=_fraction(pareto_counts[ParetoClientImpact.PARETO_HARMED], len(attack_movements)),
            tradeoff_fpr_better_tpr_worse=_fraction(
                pareto_counts[ParetoClientImpact.TRADEOFF_FPR_BETTER_TPR_WORSE], len(attack_movements)
            ),
            tradeoff_fpr_worse_tpr_better=_fraction(
                pareto_counts[ParetoClientImpact.TRADEOFF_FPR_WORSE_TPR_BETTER], len(attack_movements)
            ),
            no_fpr_change=_fraction(pareto_counts[ParetoClientImpact.NO_FPR_CHANGE], len(attack_movements)),
        ),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )


def summarize_client_impact_campaign(
    cohorts: tuple[ThresholdMovementCohort, ...],
) -> ClientImpactCampaignSummary:
    summaries = tuple(summarize_client_impact(cohort) for cohort in cohorts)
    if not summaries:
        raise ValueError("client-impact campaign requires at least one seed cohort")
    return ClientImpactCampaignSummary(
        seed_summaries=summaries,
        device_frequencies=_device_frequencies(cohorts),
        fpr_helped=_summarize_fractions(tuple(item.fpr_helped for item in summaries)),
        fpr_harmed=_summarize_fractions(tuple(item.fpr_harmed for item in summaries)),
        fpr_unchanged=_summarize_fractions(tuple(item.fpr_unchanged for item in summaries)),
        tpr_loss=_summarize_fractions(tuple(item.tpr_loss for item in summaries)),
        macro_f1_loss=_summarize_fractions(tuple(item.macro_f1_loss for item in summaries)),
        balanced_accuracy_loss=_summarize_fractions(tuple(item.balanced_accuracy_loss for item in summaries)),
        pareto_improved=_summarize_fractions(tuple(item.pareto.pareto_improved for item in summaries)),
        pareto_harmed=_summarize_fractions(tuple(item.pareto.pareto_harmed for item in summaries)),
        tradeoff_fpr_better_tpr_worse=_summarize_fractions(
            tuple(item.pareto.tradeoff_fpr_better_tpr_worse for item in summaries)
        ),
        tradeoff_fpr_worse_tpr_better=_summarize_fractions(
            tuple(item.pareto.tradeoff_fpr_worse_tpr_better for item in summaries)
        ),
        no_fpr_change=_summarize_fractions(tuple(item.pareto.no_fpr_change for item in summaries)),
    )


def _pareto_category(fpr_relief: float, tpr_change: float) -> ParetoClientImpact:
    if fpr_relief == 0.0:
        return ParetoClientImpact.NO_FPR_CHANGE
    if fpr_relief > 0.0:
        return (
            ParetoClientImpact.PARETO_IMPROVED
            if tpr_change >= 0.0
            else ParetoClientImpact.TRADEOFF_FPR_BETTER_TPR_WORSE
        )
    return ParetoClientImpact.PARETO_HARMED if tpr_change <= 0.0 else ParetoClientImpact.TRADEOFF_FPR_WORSE_TPR_BETTER


def _fraction(numerator: int, denominator: int) -> ClientImpactFraction:
    if denominator <= 0:
        raise ValueError("client-impact denominator must be positive")
    return ClientImpactFraction(
        numerator=PairedObservationCount(numerator),
        denominator=ClientCount(denominator),
        value=Ratio(numerator / denominator),
        reason=None,
    )


def _loss_fraction(values: tuple[float, ...], reason: str) -> ClientImpactFraction:
    return (
        _unavailable_fraction(AnalysisReasonText(reason))
        if not values
        else _fraction(sum(value < 0.0 for value in values), len(values))
    )


def _unavailable_fraction(reason: AnalysisReasonText) -> ClientImpactFraction:
    return ClientImpactFraction(numerator=None, denominator=None, value=None, reason=reason)


def _magnitude_summary(values: tuple[float, ...], reason: str) -> ClientImpactMagnitudeSummary:
    if not values:
        return _unavailable_magnitude(AnalysisReasonText(reason))
    ordered = tuple(sorted(values))
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return ClientImpactMagnitudeSummary(median=MetricValue(median), maximum=MetricValue(ordered[-1]), reason=None)


def _unavailable_magnitude(reason: AnalysisReasonText) -> ClientImpactMagnitudeSummary:
    return ClientImpactMagnitudeSummary(median=None, maximum=None, reason=reason)


def _summarize_fractions(values: tuple[ClientImpactFraction, ...]) -> ClientImpactFractionSummary:
    available = tuple(item.value.value for item in values if item.value is not None)
    unavailable = len(values) - len(available)
    if not available:
        return ClientImpactFractionSummary(
            seed_values=values,
            valid_seed_count=SeedObservationCount(0),
            unavailable_seed_count=SeedObservationCount(unavailable),
            arithmetic_mean=None,
            median=None,
            minimum=None,
            maximum=None,
        )
    ordered = tuple(sorted(available))
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return ClientImpactFractionSummary(
        seed_values=values,
        valid_seed_count=SeedObservationCount(len(available)),
        unavailable_seed_count=SeedObservationCount(unavailable),
        arithmetic_mean=MetricValue(sum(available) / len(available)),
        median=MetricValue(median),
        minimum=MetricValue(ordered[0]),
        maximum=MetricValue(ordered[-1]),
    )


def _device_frequencies(cohorts: tuple[ThresholdMovementCohort, ...]) -> tuple[ClientImpactDeviceFrequency, ...]:
    movements_by_client: dict[ClientIdentity, list[ThresholdMovement]] = {}
    for cohort in cohorts:
        if cohort.availability is not AvailabilityStatus.AVAILABLE:
            continue
        for movement in cohort.movements:
            movements_by_client.setdefault(movement.client, []).append(movement)
    frequencies: list[ClientImpactDeviceFrequency] = []
    for client, movements in sorted(movements_by_client.items()):
        seeds = tuple(movement.seed for movement in movements)
        if len(seeds) != len(frozenset(seeds)):
            raise ValueError("client-impact device frequency cannot repeat a client seed")
        fpr_relief = tuple(-movement.delta_fpr.value for movement in movements)
        attack_movements = tuple(movement for movement in movements if movement.delta_tpr is not None)
        tpr_loss = (
            _unavailable_fraction(AnalysisReasonText("no valid TPR seeds for client"))
            if not attack_movements
            else _fraction(
                sum(movement.delta_tpr.value < 0.0 for movement in attack_movements if movement.delta_tpr is not None),
                len(attack_movements),
            )
        )
        frequencies.append(
            ClientImpactDeviceFrequency(
                client=client,
                observed_seed_count=SeedObservationCount(len(movements)),
                fpr_help_frequency=_fraction(sum(value > 0.0 for value in fpr_relief), len(movements)),
                fpr_harm_frequency=_fraction(sum(value < 0.0 for value in fpr_relief), len(movements)),
                tpr_loss_frequency=tpr_loss,
            )
        )
    return tuple(frequencies)
