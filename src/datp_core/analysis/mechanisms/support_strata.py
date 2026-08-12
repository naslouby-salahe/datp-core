from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.mechanisms.movement import ThresholdMovementCohort
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, PopulationId
from datp_core.core.numeric import ClientCount, MetricValue, Seed
from datp_core.data.nbaiot.schema import NBaIoTDevice
from datp_core.data.populations.contracts import ClientIdentity


class CalibrationSupportStratum(StrEnum):
    LOW_SUPPORT = "low_support"
    MID_SUPPORT = "mid_support"
    HIGH_SUPPORT = "high_support"


class CampaignFixedSupportStratum(StrictModel):
    client: ClientIdentity
    support_score: MetricValue
    ascending_rank: ClientCount
    stratum: CalibrationSupportStratum


class CampaignFixedSupportStrata(StrictModel):
    entries: tuple[CampaignFixedSupportStratum, ...]
    availability: AvailabilityStatus
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_strata(self) -> "CampaignFixedSupportStrata":
        if self.availability is AvailabilityStatus.AVAILABLE:
            if len(self.entries) != len(NBaIoTDevice) or self.reason is not None:
                raise ValueError("available support strata require exactly nine N-BaIoT devices")
        elif self.entries or self.reason is None:
            raise ValueError("unavailable support strata require no entries and an explicit reason")
        return self


class SupportStratumSeedOutcome(StrictModel):
    seed: Seed
    stratum: CalibrationSupportStratum
    mean_fpr_relief: MetricValue
    fpr_helped_fraction: MetricValue
    fpr_harmed_fraction: MetricValue
    shared_mean_absolute_target_error: MetricValue
    local_mean_absolute_target_error: MetricValue


class SupportStratumOutcomeReport(StrictModel):
    outcomes: tuple[SupportStratumSeedOutcome, ...]
    availability: AvailabilityStatus
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_outcomes(self) -> "SupportStratumOutcomeReport":
        if self.availability is AvailabilityStatus.AVAILABLE:
            if not self.outcomes or self.reason is not None:
                raise ValueError("available support-stratum outcomes require data and no reason")
        elif self.outcomes or self.reason is None:
            raise ValueError("unavailable support-stratum outcomes require no data and a reason")
        return self


def campaign_fixed_support_strata(
    documents: tuple[FederatedEvaluationDocument, ...],
) -> CampaignFixedSupportStrata:
    if not documents:
        return _unavailable("no confirmatory shared-policy evaluation documents")
    if any(document.score_coordinate.population is not PopulationId.NBAIOT_NATURAL_DEVICES for document in documents):
        return _unavailable("support strata apply only to the N-BaIoT natural-device population")
    counts_by_client: dict[ClientIdentity, list[int]] = {}
    for document in documents:
        supports = document.diagnostics.calibration_support
        if not supports:
            return _unavailable("evaluation document lacks calibration-support provenance")
        for support in supports:
            counts_by_client.setdefault(support.client, []).append(support.source_benign_calibration_count.value)
    expected_seed_count = len(documents)
    if (
        len(counts_by_client) != len(NBaIoTDevice)
        or any(len(counts) != expected_seed_count for counts in counts_by_client.values())
    ):
        return _unavailable("expected exactly nine eligible N-BaIoT devices across every declared seed")
    ordered = tuple(sorted(counts_by_client.items(), key=lambda item: (_median(item[1]), item[0].client_id.value)))
    entries = tuple(
        CampaignFixedSupportStratum(
            client=client,
            support_score=MetricValue(_median(counts)),
            ascending_rank=ClientCount(index),
            stratum=_stratum_for_rank(index),
        )
        for index, (client, counts) in enumerate(ordered, start=1)
    )
    return CampaignFixedSupportStrata(entries=entries, availability=AvailabilityStatus.AVAILABLE, reason=None)


def support_stratum_seed_outcomes(
    strata: CampaignFixedSupportStrata,
    policy_pairs: tuple[tuple[FederatedEvaluationDocument, FederatedEvaluationDocument], ...],
    movement_cohorts: tuple[ThresholdMovementCohort, ...],
) -> SupportStratumOutcomeReport:
    if strata.availability is AvailabilityStatus.UNAVAILABLE:
        return _unavailable_outcomes(strata.reason or AnalysisReasonText("support strata unavailable"))
    if len(policy_pairs) != len(movement_cohorts):
        return _unavailable_outcomes(AnalysisReasonText("policy and movement seed evidence counts differ"))
    members = {
        stratum: tuple(entry.client for entry in strata.entries if entry.stratum is stratum)
        for stratum in CalibrationSupportStratum
    }
    outcomes: list[SupportStratumSeedOutcome] = []
    for (shared, local), cohort in zip(policy_pairs, movement_cohorts, strict=True):
        if not cohort.movements:
            return _unavailable_outcomes(AnalysisReasonText("support-stratum outcomes require movement observations"))
        movements = {item.client: item for item in cohort.movements}
        shared_errors = {
            item.client: item.absolute_target_error for item in shared.diagnostics.held_out_operating_points
        }
        local_errors = {
            item.client: item.absolute_target_error for item in local.diagnostics.held_out_operating_points
        }
        for stratum, clients in members.items():
            if any(
                client not in movements or client not in shared_errors or client not in local_errors
                for client in clients
            ):
                return _unavailable_outcomes(
                    AnalysisReasonText("support-stratum members lack paired operating evidence")
                )
            fpr_relief = tuple(-movements[client].delta_fpr.value for client in clients)
            outcomes.append(
                SupportStratumSeedOutcome(
                    seed=shared.score_coordinate.training_seed,
                    stratum=stratum,
                    mean_fpr_relief=MetricValue(sum(fpr_relief) / len(fpr_relief)),
                    fpr_helped_fraction=MetricValue(sum(value > 0.0 for value in fpr_relief) / len(fpr_relief)),
                    fpr_harmed_fraction=MetricValue(sum(value < 0.0 for value in fpr_relief) / len(fpr_relief)),
                    shared_mean_absolute_target_error=MetricValue(
                        sum(shared_errors[client].value for client in clients) / len(clients)
                    ),
                    local_mean_absolute_target_error=MetricValue(
                        sum(local_errors[client].value for client in clients) / len(clients)
                    ),
                )
            )
    return SupportStratumOutcomeReport(outcomes=tuple(outcomes), availability=AvailabilityStatus.AVAILABLE, reason=None)


def _median(values: list[int]) -> float:
    ordered = tuple(sorted(values))
    middle = len(ordered) // 2
    return float(ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0)


def _stratum_for_rank(rank: int) -> CalibrationSupportStratum:
    if rank <= 3:
        return CalibrationSupportStratum.LOW_SUPPORT
    if rank <= 6:
        return CalibrationSupportStratum.MID_SUPPORT
    return CalibrationSupportStratum.HIGH_SUPPORT


def _unavailable(reason: str) -> CampaignFixedSupportStrata:
    return CampaignFixedSupportStrata(
        entries=(), availability=AvailabilityStatus.UNAVAILABLE, reason=AnalysisReasonText(reason)
    )


def _unavailable_outcomes(reason: AnalysisReasonText) -> SupportStratumOutcomeReport:
    return SupportStratumOutcomeReport(outcomes=(), availability=AvailabilityStatus.UNAVAILABLE, reason=reason)
