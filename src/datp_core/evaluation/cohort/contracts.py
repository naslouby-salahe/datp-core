"""Persisted threshold-independent evaluation cohort contracts."""

from enum import StrEnum

from pydantic import model_validator

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvaluationCohort, PopulationId
from datp_core.domain.values import CalibrationSize, RowCount, Seed
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
        if min(
            self.benign_calibration_count,
            self.benign_evaluation_count,
            self.attack_evaluation_count,
        ) < 0:
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
