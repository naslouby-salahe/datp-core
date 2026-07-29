"""Threshold-independent evaluation cohort construction."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CapabilityStatus,
    EvaluationCohort,
    FederatedThresholdMethod,
    PopulationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CalibrationSize, Seed
from datp_core.populations.capabilities import population_capabilities
from datp_core.populations.models import PopulationCapabilities
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT


class ClientExclusionReason(StrEnum):
    INSUFFICIENT_BENIGN_CALIBRATION = "insufficient_benign_calibration"
    EMPTY_BENIGN_EVALUATION = "empty_benign_evaluation"
    INVALID_ATTACK_ASSIGNMENT = "invalid_attack_assignment"
    NO_HELD_OUT_ATTACK_ROWS = "no_held_out_attack_rows"
    POPULATION_PROHIBITS_FPR = "population_prohibits_fpr"
    POPULATION_PROHIBITS_ATTACK_METRICS = "population_prohibits_attack_metrics"
    INVALID_CHRONOLOGY = "invalid_chronology"
    DEPLOYMENT_FALLBACK_ONLY = "deployment_fallback_only"
    CLIENT_NOT_ACCEPTED = "client_not_accepted"


class ClientEligibilityRecord(StrictModel):

    client_id: str
    population: PopulationId
    benign_calibration_count: int
    benign_evaluation_count: int
    attack_evaluation_count: int
    confirmatory_eligible: bool
    attack_evaluable: bool
    deployment_fallback: bool
    exclusion_reasons: tuple[ClientExclusionReason, ...]

    @model_validator(mode="after")
    def validate_record(self) -> "ClientEligibilityRecord":
        if not self.client_id:
            raise ValueError("client eligibility requires a client identity")
        if min(self.benign_calibration_count, self.benign_evaluation_count, self.attack_evaluation_count) < 0:
            raise ValueError("cohort counts must be non-negative")
        if self.confirmatory_eligible and self.deployment_fallback:
            raise ValueError("deployment-fallback clients cannot be confirmatory eligible")
        if (
            self.confirmatory_eligible
            and ClientExclusionReason.INSUFFICIENT_BENIGN_CALIBRATION in self.exclusion_reasons
        ):
            raise ValueError("confirmatory-eligible clients cannot record insufficient calibration")
        return self


class EvaluationCohortMembership(StrictModel):

    client_id: str
    cohort: EvaluationCohort
    reasons: tuple[ClientExclusionReason, ...]

    @model_validator(mode="after")
    def validate_membership(self) -> "EvaluationCohortMembership":
        if not self.client_id:
            raise ValueError("cohort membership requires a client identity")
        if self.cohort is EvaluationCohort.CONFIRMATORY_ELIGIBLE and self.reasons:
            raise ValueError("confirmatory-eligible membership cannot carry exclusion reasons")
        if self.cohort is EvaluationCohort.UNAVAILABLE and not self.reasons:
            raise ValueError("unavailable membership requires at least one exclusion reason")
        return self


class EvaluationCohortManifest(StrictModel):

    population: PopulationId
    partition_seed: Seed
    minimum_benign_calibration_support: CalibrationSize
    records: tuple[ClientEligibilityRecord, ...]
    memberships: tuple[EvaluationCohortMembership, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> "EvaluationCohortManifest":
        record_ids = tuple(record.client_id for record in self.records)
        if len(record_ids) != len(frozenset(record_ids)):
            raise ValueError("cohort records must be unique by client")
        if self.minimum_benign_calibration_support != MINIMUM_BENIGN_SUPPORT:
            raise ValueError("cohort manifests must use the locked minimum benign calibration support")
        confirmatory = frozenset(
            item.client_id for item in self.memberships if item.cohort is EvaluationCohort.CONFIRMATORY_ELIGIBLE
        )
        fallback = frozenset(
            item.client_id for item in self.memberships if item.cohort is EvaluationCohort.DEPLOYMENT_FALLBACK
        )
        if confirmatory & fallback:
            raise ValueError("deployment-fallback clients cannot enter the confirmatory cohort")
        return self


@dataclass(frozen=True, slots=True)
class ClientPartitionCounts:
    client_id: str
    benign_calibration_count: int
    benign_evaluation_count: int
    attack_evaluation_count: int
    accepted: bool
    deployment_fallback: bool


def build_evaluation_cohort_manifest(
    *,
    population: PopulationId,
    partition_seed: Seed,
    client_counts: tuple[ClientPartitionCounts, ...],
    threshold_method: FederatedThresholdMethod | None = None,
) -> EvaluationCohortManifest:
    """Construct threshold-independent cohorts.

    ``threshold_method`` is accepted only to prove invariance: it must not alter membership.
    """
    del threshold_method  # explicit non-use: cohorts never depend on threshold identity
    capabilities = population_capabilities(population)
    support = MINIMUM_BENIGN_SUPPORT
    records: list[ClientEligibilityRecord] = []
    memberships: list[EvaluationCohortMembership] = []
    for counts in sorted(client_counts, key=lambda item: item.client_id):
        record, client_memberships = _classify_client(population, capabilities.confirmatory_eligible, support, counts)
        records.append(record)
        memberships.extend(client_memberships)
    return EvaluationCohortManifest(
        population=population,
        partition_seed=partition_seed,
        minimum_benign_calibration_support=support,
        records=tuple(records),
        memberships=tuple(memberships),
    )


def assert_cohort_invariant_to_threshold_methods(
    *,
    population: PopulationId,
    partition_seed: Seed,
    client_counts: tuple[ClientPartitionCounts, ...],
    methods: tuple[FederatedThresholdMethod, ...],
) -> EvaluationCohortManifest:
    if not methods:
        raise ScientificContractError(
            "cohort invariance requires at least one threshold method identity",
            subject=population,
            reason="invariance cannot be demonstrated over an empty method set",
        )
    baseline = build_evaluation_cohort_manifest(
        population=population,
        partition_seed=partition_seed,
        client_counts=client_counts,
        threshold_method=methods[0],
    )
    for method in methods[1:]:
        candidate = build_evaluation_cohort_manifest(
            population=population,
            partition_seed=partition_seed,
            client_counts=client_counts,
            threshold_method=method,
        )
        if candidate != baseline:
            raise ScientificContractError(
                "evaluation cohorts changed across threshold methods",
                subject=population,
                reason="eligibility is decided before threshold construction and must be reused",
            )
    return baseline


def _classify_client(
    population: PopulationId,
    population_confirmatory: bool,
    support: CalibrationSize,
    counts: ClientPartitionCounts,
) -> tuple[ClientEligibilityRecord, tuple[EvaluationCohortMembership, ...]]:
    capabilities = population_capabilities(population)
    reasons = _support_exclusion_reasons(counts, support, capabilities.fpr_evaluation)
    confirmatory = _is_confirmatory(population_confirmatory, counts, support, reasons)
    attack_reasons = _attack_exclusion_reasons(counts, capabilities)
    attack_evaluable = counts.accepted and not attack_reasons
    memberships = _cohort_memberships(counts, confirmatory, attack_evaluable, reasons, attack_reasons)
    record = ClientEligibilityRecord(
        client_id=counts.client_id,
        population=population,
        benign_calibration_count=counts.benign_calibration_count,
        benign_evaluation_count=counts.benign_evaluation_count,
        attack_evaluation_count=counts.attack_evaluation_count,
        confirmatory_eligible=confirmatory,
        attack_evaluable=attack_evaluable,
        deployment_fallback=counts.deployment_fallback,
        exclusion_reasons=tuple(dict.fromkeys((*reasons, *attack_reasons))),
    )
    return record, memberships


def _support_exclusion_reasons(
    counts: ClientPartitionCounts,
    support: CalibrationSize,
    fpr_status: CapabilityStatus,
) -> list[ClientExclusionReason]:
    reasons: list[ClientExclusionReason] = []
    if not counts.accepted:
        reasons.append(ClientExclusionReason.CLIENT_NOT_ACCEPTED)
    if counts.benign_calibration_count < support.value:
        reasons.append(ClientExclusionReason.INSUFFICIENT_BENIGN_CALIBRATION)
    if counts.benign_evaluation_count < 1:
        reasons.append(ClientExclusionReason.EMPTY_BENIGN_EVALUATION)
    if fpr_status is CapabilityStatus.UNAVAILABLE:
        reasons.append(ClientExclusionReason.POPULATION_PROHIBITS_FPR)
    return reasons


def _is_confirmatory(
    population_confirmatory: bool,
    counts: ClientPartitionCounts,
    support: CalibrationSize,
    reasons: list[ClientExclusionReason],
) -> bool:
    return (
        population_confirmatory
        and counts.accepted
        and counts.benign_calibration_count >= support.value
        and counts.benign_evaluation_count >= 1
        and not counts.deployment_fallback
        and ClientExclusionReason.POPULATION_PROHIBITS_FPR not in reasons
    )


def _attack_exclusion_reasons(
    counts: ClientPartitionCounts,
    capabilities: PopulationCapabilities,
) -> list[ClientExclusionReason]:
    reasons: list[ClientExclusionReason] = []
    if capabilities.client_level_attack_assignment in {
        CapabilityStatus.UNAVAILABLE,
        CapabilityStatus.NOT_APPLICABLE,
    }:
        reasons.append(ClientExclusionReason.INVALID_ATTACK_ASSIGNMENT)
    if capabilities.attack_sensitive_evaluation in {
        CapabilityStatus.UNAVAILABLE,
        CapabilityStatus.NOT_APPLICABLE,
    }:
        reasons.append(ClientExclusionReason.POPULATION_PROHIBITS_ATTACK_METRICS)
    if counts.attack_evaluation_count < 1:
        reasons.append(ClientExclusionReason.NO_HELD_OUT_ATTACK_ROWS)
    return reasons


def _cohort_memberships(
    counts: ClientPartitionCounts,
    confirmatory: bool,
    attack_evaluable: bool,
    reasons: list[ClientExclusionReason],
    attack_reasons: list[ClientExclusionReason],
) -> tuple[EvaluationCohortMembership, ...]:
    memberships: list[EvaluationCohortMembership] = []
    if confirmatory:
        memberships.append(
            EvaluationCohortMembership(
                client_id=counts.client_id,
                cohort=EvaluationCohort.CONFIRMATORY_ELIGIBLE,
                reasons=(),
            )
        )
    if attack_evaluable:
        memberships.append(
            EvaluationCohortMembership(
                client_id=counts.client_id,
                cohort=EvaluationCohort.ATTACK_EVALUABLE,
                reasons=(),
            )
        )
    if counts.deployment_fallback:
        memberships.append(
            EvaluationCohortMembership(
                client_id=counts.client_id,
                cohort=EvaluationCohort.DEPLOYMENT_FALLBACK,
                reasons=(ClientExclusionReason.DEPLOYMENT_FALLBACK_ONLY, *tuple(reasons)),
            )
        )
    if not confirmatory and not attack_evaluable:
        unavailable = tuple(dict.fromkeys((*reasons, *attack_reasons))) or (
            ClientExclusionReason.CLIENT_NOT_ACCEPTED,
        )
        memberships.append(
            EvaluationCohortMembership(
                client_id=counts.client_id,
                cohort=EvaluationCohort.UNAVAILABLE,
                reasons=unavailable,
            )
        )
    return tuple(memberships)
