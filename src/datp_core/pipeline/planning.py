"""Deterministic experiment-plan expansion and feasibility recording."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import blake2b

from datp_core.domain.enums import (
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TemporalState,
    TrainingModelId,
)
from datp_core.domain.values import Seed
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT


class PlanDisposition(StrEnum):
    EXECUTABLE = "executable"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningEvidence:
    experiment: ExperimentId
    disposition: PlanDisposition
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("planning evidence requires a non-empty reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentCoordinate:
    experiment: ExperimentId
    population: PopulationId
    training_model: TrainingModelId
    training_seed: Seed
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None

    @property
    def stable_key(self) -> str:
        temporal = self.temporal_state.value if self.temporal_state is not None else "static"
        return "/".join(
            (
                self.experiment.value,
                self.population.value,
                self.training_model.value,
                str(self.training_seed.value),
                self.threshold_method.value,
                self.metric.value,
                temporal,
            )
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PlannedExperiment:
    coordinate: ExperimentCoordinate
    disposition: PlanDisposition
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("planned experiments require a non-empty reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentPlan:
    entries: tuple[PlannedExperiment, ...]
    digest: str

    def __post_init__(self) -> None:
        keys = tuple(entry.coordinate.stable_key for entry in self.entries)
        if keys != tuple(sorted(keys)):
            raise ValueError("experiment-plan entries must be in deterministic order")
        if len(keys) != len(frozenset(keys)):
            raise ValueError("experiment-plan coordinates must be unique")
        expected = _digest_entries(self.entries)
        if self.digest != expected:
            raise ValueError("experiment-plan digest does not match its entries")

    @property
    def executable(self) -> tuple[PlannedExperiment, ...]:
        return tuple(entry for entry in self.entries if entry.disposition is PlanDisposition.EXECUTABLE)


def expand_experiment_plan(
    *,
    declarations: tuple[ExperimentDeclaration, ...] = EXPERIMENTS,
    seed_cohort: SeedCohort = CONFIRMATORY_SEED_COHORT,
    evidence: tuple[PlanningEvidence, ...] = (),
) -> ExperimentPlan:
    evidence_by_experiment = _validated_evidence(evidence)
    entries = tuple(
        sorted(
            (
                _planned_entry(declaration, seed, threshold_method, metric, evidence_by_experiment)
                for declaration in declarations
                for seed in seed_cohort.values
                for threshold_method in declaration.federated_thresholds
                for metric in declaration.metrics
            ),
            key=lambda entry: entry.coordinate.stable_key,
        )
    )
    return ExperimentPlan(entries=entries, digest=_digest_entries(entries))


def _planned_entry(
    declaration: ExperimentDeclaration,
    seed: Seed,
    threshold_method: FederatedThresholdMethod,
    metric: MetricId,
    evidence: tuple[PlanningEvidence, ...],
) -> PlannedExperiment:
    disposition, reason = _resolve_disposition(declaration, evidence)
    return PlannedExperiment(
        coordinate=ExperimentCoordinate(
            experiment=declaration.id,
            population=declaration.population,
            training_model=declaration.training_model,
            training_seed=seed,
            threshold_method=threshold_method,
            metric=metric,
            temporal_state=None,
        ),
        disposition=disposition,
        reason=reason,
    )


def _resolve_disposition(
    declaration: ExperimentDeclaration,
    evidence: tuple[PlanningEvidence, ...],
) -> tuple[PlanDisposition, str]:
    explicit = tuple(item for item in evidence if item.experiment is declaration.id)
    if explicit:
        item = explicit[0]
        return item.disposition, item.reason
    match declaration.readiness:
        case ExperimentReadiness.EXECUTABLE:
            return PlanDisposition.EXECUTABLE, "declared executable by the validated protocol graph"
        case ExperimentReadiness.SUPPRESSED:
            return PlanDisposition.SUPPRESSED, "suppressed by the validated protocol graph"
        case ExperimentReadiness.INFEASIBLE:
            return PlanDisposition.INFEASIBLE, "declared infeasible by the validated protocol graph"
        case ExperimentReadiness.BLOCKED:
            return PlanDisposition.BLOCKED, "blocked by an unresolved scientific or artifact prerequisite"
        case ExperimentReadiness.DECLARED:
            return PlanDisposition.BLOCKED, "declared experiment requires explicit feasibility evidence"


def _validated_evidence(evidence: tuple[PlanningEvidence, ...]) -> tuple[PlanningEvidence, ...]:
    experiments = tuple(item.experiment for item in evidence)
    if len(experiments) != len(frozenset(experiments)):
        raise ValueError("planning evidence must be unique by experiment")
    return evidence


def _digest_entries(entries: tuple[PlannedExperiment, ...]) -> str:
    payload = "\n".join(
        f"{entry.coordinate.stable_key}|{entry.disposition.value}|{entry.reason}" for entry in entries
    ).encode("utf-8")
    return blake2b(payload, digest_size=32).hexdigest()
