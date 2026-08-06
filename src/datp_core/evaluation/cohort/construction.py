"""Pure threshold-independent evaluation cohort classification."""

from datp_core.datasets.partitioning.contracts import (
    ClientIdentity,
    ClientPartitionCounts,
    PopulationCapabilities,
)
from datp_core.datasets.registry import population_capabilities
from datp_core.domain.enums import (
    CapabilityStatus,
    ContractSubject,
    EvaluationCohort,
    FederatedThresholdMethod,
    PopulationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CalibrationSize, Seed
from datp_core.evaluation.cohort.contracts import (
    ClientEligibilityRecord,
    ClientExclusionReason,
    EvaluationCohortManifest,
    EvaluationCohortMembership,
)
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT


def build_evaluation_cohort_manifest(
    *,
    population: PopulationId,
    partition_seed: Seed,
    client_counts: tuple[ClientPartitionCounts, ...],
) -> EvaluationCohortManifest:
    """Construct threshold-independent cohorts from already measured support counts."""
    support = MINIMUM_BENIGN_SUPPORT
    capabilities = population_capabilities(population)
    records: list[ClientEligibilityRecord] = []
    memberships: list[EvaluationCohortMembership] = []
    for counts in sorted(client_counts, key=lambda item: item.client):
        client = counts.client
        if client.population is not population or client.identity_kind is not capabilities.identity_kind:
            raise ScientificContractError(
                "client support counts must match the cohort population identity contract",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        record, client_memberships = _classify_client(client, support, counts, capabilities)
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
    )
    for _method in methods[1:]:
        candidate = build_evaluation_cohort_manifest(
            population=population,
            partition_seed=partition_seed,
            client_counts=client_counts,
        )
        if candidate != baseline:
            raise ScientificContractError(
                "evaluation cohorts changed across threshold methods",
                subject=population,
                reason="eligibility is decided before threshold construction and must be reused",
            )
    return baseline


def cohort_record_for_client(
    cohort: EvaluationCohortManifest,
    client: ClientIdentity,
) -> ClientEligibilityRecord | None:
    matches = tuple(record for record in cohort.records if record.client == client)
    if len(matches) > 1:
        raise ScientificContractError("evaluation cohort cannot repeat a client")
    return matches[0] if matches else None


def _classify_client(
    client: ClientIdentity,
    support: CalibrationSize,
    counts: ClientPartitionCounts,
    capabilities: PopulationCapabilities,
) -> tuple[ClientEligibilityRecord, tuple[EvaluationCohortMembership, ...]]:
    reasons = _support_exclusion_reasons(counts, support, capabilities.fpr_evaluation)
    calibration_eligible = _is_calibration_eligible(counts, support)
    fpr_evaluable = _is_fpr_evaluable(calibration_eligible, reasons)
    attack_reasons = _attack_exclusion_reasons(counts, capabilities)
    attack_evaluable = counts.accepted and not attack_reasons
    memberships = _cohort_memberships(
        client,
        counts,
        fpr_evaluable,
        attack_evaluable,
        reasons,
        attack_reasons,
    )
    record = ClientEligibilityRecord(
        client=client,
        benign_calibration_count=counts.benign_calibration_count,
        benign_evaluation_count=counts.benign_evaluation_count,
        attack_evaluation_count=counts.attack_evaluation_count,
        calibration_eligible=calibration_eligible,
        fpr_evaluable=fpr_evaluable,
        attack_evaluable=attack_evaluable,
        deployment_fallback=counts.deployment_fallback,
        exclusion_reasons=_unique_reasons((*reasons, *attack_reasons)),
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
    if counts.benign_calibration_count < support:
        reasons.append(ClientExclusionReason.INSUFFICIENT_BENIGN_CALIBRATION)
    if counts.benign_evaluation_count < 1:
        reasons.append(ClientExclusionReason.EMPTY_BENIGN_EVALUATION)
    if fpr_status is CapabilityStatus.UNAVAILABLE:
        reasons.append(ClientExclusionReason.POPULATION_PROHIBITS_FPR)
    return reasons


def _is_calibration_eligible(counts: ClientPartitionCounts, support: CalibrationSize) -> bool:
    return counts.accepted and counts.benign_calibration_count >= support and not counts.deployment_fallback


def _is_fpr_evaluable(
    calibration_eligible: bool,
    reasons: list[ClientExclusionReason],
) -> bool:
    return calibration_eligible and not any(
        reason
        in {
            ClientExclusionReason.EMPTY_BENIGN_EVALUATION,
            ClientExclusionReason.POPULATION_PROHIBITS_FPR,
        }
        for reason in reasons
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
    client: ClientIdentity,
    counts: ClientPartitionCounts,
    fpr_evaluable: bool,
    attack_evaluable: bool,
    reasons: list[ClientExclusionReason],
    attack_reasons: list[ClientExclusionReason],
) -> tuple[EvaluationCohortMembership, ...]:
    memberships: list[EvaluationCohortMembership] = []
    if fpr_evaluable:
        memberships.append(
            EvaluationCohortMembership(
                client=client,
                cohort=EvaluationCohort.FPR_EVALUABLE,
                reasons=(),
            )
        )
    if attack_evaluable:
        memberships.append(
            EvaluationCohortMembership(
                client=client,
                cohort=EvaluationCohort.ATTACK_EVALUABLE,
                reasons=(),
            )
        )
    if counts.deployment_fallback:
        memberships.append(
            EvaluationCohortMembership(
                client=client,
                cohort=EvaluationCohort.DEPLOYMENT_FALLBACK,
                reasons=(ClientExclusionReason.DEPLOYMENT_FALLBACK_ONLY, *tuple(reasons)),
            )
        )
    if not fpr_evaluable and not attack_evaluable:
        memberships.append(
            EvaluationCohortMembership(
                client=client,
                cohort=EvaluationCohort.UNAVAILABLE,
                reasons=_unique_reasons((*reasons, *attack_reasons))
                or (ClientExclusionReason.CLIENT_NOT_ACCEPTED,),
            )
        )
    return tuple(memberships)


def _unique_reasons(
    reasons: tuple[ClientExclusionReason, ...],
) -> tuple[ClientExclusionReason, ...]:
    unique: list[ClientExclusionReason] = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return tuple(unique)
