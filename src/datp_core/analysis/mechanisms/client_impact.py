from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.mechanisms.movement import ThresholdMovementCohort
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, ExperimentId
from datp_core.core.numeric import ClientCount, PairedObservationCount, Ratio, Seed


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
    def validate_availability(self) -> "ClientImpactFraction":
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
    def validate_common_attack_cohort(self) -> "ParetoClientImpactFractions":
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
    pareto: ParetoClientImpactFractions
    availability: AvailabilityStatus
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_seed_summary(self) -> "ClientImpactSeedSummary":
        if self.availability is AvailabilityStatus.AVAILABLE:
            if self.reason is not None or self.fpr_helped.value is None:
                raise ValueError("available client-impact summary requires FPR fractions and no reason")
        elif self.reason is None:
            raise ValueError("unavailable client-impact summary requires a reason")
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
