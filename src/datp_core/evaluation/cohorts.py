"""Threshold-independent evaluation cohort construction."""

from enum import StrEnum

import polars as pl
from pydantic import model_validator

from datp_core.datasets.partitioning.contracts import (
    ClientIdentity,
    ClientPartitionCounts,
    PopulationCapabilities,
    PopulationOutcomeLabel,
)
from datp_core.datasets.registry import population_capabilities
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CapabilityStatus,
    ContractSubject,
    EvaluationCohort,
    FederatedThresholdMethod,
    PopulationId,
    ScoreFrameColumn,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CalibrationSize, RowCount, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT
from datp_core.protocols.inference import ScoreArtifactManifest, ScoreRecord

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]


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
    client: ClientIdentity
    benign_calibration_count: RowCount
    benign_evaluation_count: RowCount
    attack_evaluation_count: RowCount
    calibration_eligible: bool
    fpr_evaluable: bool
    attack_evaluable: bool
    deployment_fallback: bool
    exclusion_reasons: tuple[ClientExclusionReason, ...]

    @model_validator(mode="after")
    def validate_record(self) -> "ClientEligibilityRecord":
        if (
            min(
                self.benign_calibration_count,
                self.benign_evaluation_count,
                self.attack_evaluation_count,
            )
            < 0
        ):
            raise ValueError("cohort counts must be non-negative")
        if self.calibration_eligible and self.deployment_fallback:
            raise ValueError("deployment-fallback clients cannot be calibration eligible")
        if self.fpr_evaluable and not self.calibration_eligible:
            raise ValueError("FPR-evaluable clients must be calibration eligible")
        if (
            self.calibration_eligible
            and ClientExclusionReason.INSUFFICIENT_BENIGN_CALIBRATION in self.exclusion_reasons
        ):
            raise ValueError("calibration-eligible clients cannot record insufficient calibration")
        return self


class EvaluationCohortMembership(StrictModel):
    client: ClientIdentity
    cohort: EvaluationCohort
    reasons: tuple[ClientExclusionReason, ...]

    @model_validator(mode="after")
    def validate_membership(self) -> "EvaluationCohortMembership":
        if self.cohort is EvaluationCohort.FPR_EVALUABLE and self.reasons:
            raise ValueError("FPR-evaluable membership cannot carry exclusion reasons")
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
        record_clients = tuple(record.client for record in self.records)
        if len(record_clients) != len(frozenset(record_clients)):
            raise ValueError("cohort records must be unique by client")
        if any(client.population is not self.population for client in record_clients):
            raise ValueError("cohort record clients must match the manifest population")
        membership_clients = tuple(item.client for item in self.memberships)
        if any(client.population is not self.population for client in membership_clients):
            raise ValueError("cohort membership clients must match the manifest population")
        if self.minimum_benign_calibration_support != MINIMUM_BENIGN_SUPPORT:
            raise ValueError("cohort manifests must use the locked minimum benign calibration support")
        fpr_evaluable = frozenset(
            item.client for item in self.memberships if item.cohort is EvaluationCohort.FPR_EVALUABLE
        )
        fallback = frozenset(
            item.client for item in self.memberships if item.cohort is EvaluationCohort.DEPLOYMENT_FALLBACK
        )
        if fpr_evaluable & fallback:
            raise ValueError("deployment-fallback clients cannot enter the FPR-evaluable cohort")
        return self


def build_evaluation_cohort_manifest(
    *,
    population: PopulationId,
    partition_seed: Seed,
    client_counts: tuple[ClientPartitionCounts, ...],
) -> EvaluationCohortManifest:
    """Construct threshold-independent cohorts."""
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
        record, client_memberships = _classify_client(
            client,
            support,
            counts,
            capabilities,
        )
        records.append(record)
        memberships.extend(client_memberships)
    return EvaluationCohortManifest(
        population=population,
        partition_seed=partition_seed,
        minimum_benign_calibration_support=support,
        records=tuple(records),
        memberships=tuple(memberships),
    )


def client_partition_counts_from_scores(
    manifest: FederatedScoreArtifactManifest,
) -> tuple[ClientPartitionCounts, ...]:
    calibration = tuple(
        sorted(
            manifest.calibration_records,
            key=lambda record: record.scored_client,
        )
    )
    evaluation = tuple(
        sorted(
            manifest.evaluation_records,
            key=lambda record: record.scored_client,
        )
    )
    if tuple(record.scored_client for record in calibration) != tuple(record.scored_client for record in evaluation):
        raise ScientificContractError("evaluation inputs require matching calibration and evaluation score clients")
    return tuple(
        ClientPartitionCounts(
            client=calibration_record.scored_client,
            benign_calibration_count=_label_count(
                calibration_record,
                PopulationOutcomeLabel.BENIGN,
            ),
            benign_evaluation_count=_label_count(
                evaluation_record,
                PopulationOutcomeLabel.BENIGN,
            ),
            attack_evaluation_count=_label_count(
                evaluation_record,
                PopulationOutcomeLabel.ATTACK,
            ),
            accepted=True,
            deployment_fallback=False,
        )
        for calibration_record, evaluation_record in zip(
            calibration,
            evaluation,
            strict=True,
        )
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
                reason=("eligibility is decided before threshold construction and must be reused"),
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
    reasons = _support_exclusion_reasons(
        counts,
        support,
        capabilities.fpr_evaluation,
    )
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


def _label_count(
    record: FederatedScoreRecord,
    label: PopulationOutcomeLabel,
) -> RowCount:
    frame = pl.read_parquet(record.path)
    return RowCount(int((frame[ScoreFrameColumn.OUTCOME_LABEL.value] == label.value).sum()))


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


def _is_calibration_eligible(
    counts: ClientPartitionCounts,
    support: CalibrationSize,
) -> bool:
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
                reasons=(
                    ClientExclusionReason.DEPLOYMENT_FALLBACK_ONLY,
                    *tuple(reasons),
                ),
            )
        )
    if not fpr_evaluable and not attack_evaluable:
        memberships.append(
            EvaluationCohortMembership(
                client=client,
                cohort=EvaluationCohort.UNAVAILABLE,
                reasons=(_unique_reasons((*reasons, *attack_reasons)) or (ClientExclusionReason.CLIENT_NOT_ACCEPTED,)),
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
