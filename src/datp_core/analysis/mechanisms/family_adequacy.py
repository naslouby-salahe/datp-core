from statistics import fmean, stdev
from typing import ClassVar

from pydantic import model_validator

from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, EvidenceRole, FamilyIdentity
from datp_core.core.numeric import MetricValue, PairedObservationCount, Seed, ThresholdValue
from datp_core.data.populations.contracts import FamilyAssignment


class FamilyExplanatoryAdequacyResult(StrictModel):
    seed: Seed
    within_family_js: MetricValue | None
    between_family_js: MetricValue | None
    family_separation_js: MetricValue | None
    within_family_pair_count: PairedObservationCount
    between_family_pair_count: PairedObservationCount
    mean_within_family_threshold_sd: MetricValue | None
    between_family_threshold_sd: MetricValue | None
    singleton_families: tuple[FamilyIdentity, ...]
    unavailable_reason: AnalysisReasonText | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "FamilyExplanatoryAdequacyResult":
        available = self.unavailable_reason is None
        values = (
            self.within_family_js,
            self.between_family_js,
            self.family_separation_js,
            self.mean_within_family_threshold_sd,
            self.between_family_threshold_sd,
        )
        if available and any(value is None for value in values):
            raise ValueError("available family adequacy requires all summary values")
        if not available and any(value is not None for value in values):
            raise ValueError("unavailable family adequacy cannot contain summary values")
        if tuple(sorted(set(self.singleton_families), key=lambda item: item.value)) != self.singleton_families:
            raise ValueError("singleton families must be unique and sorted")
        return self


def family_explanatory_adequacy(
    *,
    seed: Seed,
    divergence: DivergenceResult,
    family_by_client: tuple[FamilyAssignment, ...],
    local_thresholds: tuple[tuple[FamilyAssignment, ThresholdValue], ...],
) -> FamilyExplanatoryAdequacyResult:
    families = {item.client: item.family for item in family_by_client}
    if len(families) != len(family_by_client) or tuple(sorted(families)) != divergence.clients:
        raise ValueError("family adequacy requires family assignments for exactly the divergence clients")
    threshold_clients = tuple(sorted(assignment.client for assignment, _ in local_thresholds))
    if len(set(threshold_clients)) != len(threshold_clients) or threshold_clients != divergence.clients:
        raise ValueError("family adequacy requires one local threshold for every divergence client")
    thresholds_by_family: dict[FamilyIdentity, list[float]] = {}
    for assignment, threshold in local_thresholds:
        if families[assignment.client] != assignment.family:
            raise ValueError("family adequacy local thresholds must use the declared family assignment")
        thresholds_by_family.setdefault(assignment.family, []).append(threshold.value)
    singleton_families = tuple(
        sorted(
            (family for family, values in thresholds_by_family.items() if len(values) == 1), key=lambda item: item.value
        )
    )
    if divergence.blocker is not None:
        return _unavailable(seed, divergence.reason, singleton_families=singleton_families)
    within = tuple(
        item.value.value
        for item in divergence.pairwise_distances
        if families[item.left_client] == families[item.right_client]
    )
    between = tuple(
        item.value.value
        for item in divergence.pairwise_distances
        if families[item.left_client] != families[item.right_client]
    )
    within_sds = tuple(stdev(values) for values in thresholds_by_family.values() if len(values) >= 2)
    family_means = tuple(fmean(values) for values in thresholds_by_family.values())
    if not within or not between or not within_sds or len(family_means) < 2:
        return _unavailable(
            seed,
            AnalysisReasonText(
                "family adequacy requires within/between score pairs and at least two family threshold means"
            ),
            within_count=len(within),
            between_count=len(between),
            singleton_families=singleton_families,
        )
    within_js = MetricValue(fmean(within))
    between_js = MetricValue(fmean(between))
    return FamilyExplanatoryAdequacyResult(
        seed=seed,
        within_family_js=within_js,
        between_family_js=between_js,
        family_separation_js=MetricValue(between_js.value - within_js.value),
        within_family_pair_count=PairedObservationCount(len(within)),
        between_family_pair_count=PairedObservationCount(len(between)),
        mean_within_family_threshold_sd=MetricValue(fmean(within_sds)),
        between_family_threshold_sd=MetricValue(stdev(family_means)),
        singleton_families=singleton_families,
        unavailable_reason=None,
    )


def _unavailable(
    seed: Seed,
    reason: AnalysisReasonText | None,
    *,
    within_count: int = 0,
    between_count: int = 0,
    singleton_families: tuple[FamilyIdentity, ...],
) -> FamilyExplanatoryAdequacyResult:
    if reason is None:
        raise ValueError("unavailable family adequacy requires a reason")
    return FamilyExplanatoryAdequacyResult(
        seed=seed,
        within_family_js=None,
        between_family_js=None,
        family_separation_js=None,
        within_family_pair_count=PairedObservationCount(within_count),
        between_family_pair_count=PairedObservationCount(between_count),
        mean_within_family_threshold_sd=None,
        between_family_threshold_sd=None,
        singleton_families=singleton_families,
        unavailable_reason=reason,
    )
