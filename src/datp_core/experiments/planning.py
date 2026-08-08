"""Deterministic experiment-plan expansion and digesting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.data.populations.contracts import ControlledPartitionKind
from datp_core.data.registry import population_capabilities, population_declaration
from datp_core.core.identifiers import (
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.artifacts.provenance import Checksum, checksum_text
from datp_core.core.numeric import DirichletConcentration, ModelCoefficientValue, Quantile, Seed
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.protocols.calibration import QUANTILE_GRID
from datp_core.protocols.experiments import EXECUTION_IDENTITY_DECLARATIONS, ExperimentDeclaration
from datp_core.data.populations.declarations import DIRICHLET_CONCENTRATIONS, split_protocol_for_population
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS, FEDPROX_TRAINING_PROTOCOLS


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
    digest: Checksum

    def __post_init__(self) -> None:
        keys = tuple(entry.coordinate.stable_key for entry in self.entries)
        if keys != tuple(sorted(keys)):
            raise ValueError("experiment-plan entries must be in deterministic order")
        if len(keys) != len(frozenset(keys)):
            raise ValueError("experiment-plan coordinates must be unique")
        if self.digest != _digest_entries(self.entries):
            raise ValueError("experiment-plan digest does not match its entries")

    @property
    def executable(self) -> tuple[PlannedExperiment, ...]:
        return tuple(entry for entry in self.entries if entry.disposition is PlanDisposition.EXECUTABLE)


def merge_experiment_plans(plans: tuple[ExperimentPlan, ...]) -> ExperimentPlan:
    entries = tuple(
        sorted(
            (entry for plan in plans for entry in plan.entries),
            key=lambda entry: entry.coordinate.stable_key,
        )
    )
    return ExperimentPlan(entries=entries, digest=_digest_entries(entries))


def expand_experiment_plan(
    *,
    declarations: tuple[ExperimentDeclaration, ...],
    seed_cohort: SeedCohort,
    evidence: tuple[PlanningEvidence, ...] = (),
) -> ExperimentPlan:
    validated_evidence = _validated_evidence(evidence)
    entries = tuple(
        sorted(
            (
                _planned_entry(declaration, cell, validated_evidence)
                for declaration in declarations
                for cell in _swept_cells(declaration, seed_cohort)
            ),
            key=lambda entry: entry.coordinate.stable_key,
        )
    )
    return ExperimentPlan(entries=entries, digest=_digest_entries(entries))


@dataclass(frozen=True, slots=True, kw_only=True)
class _SweptCell:
    seed: Seed
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None
    model_coefficient: ModelCoefficientValue | None
    threshold_quantile: Quantile | None
    controlled_partition_kind: ControlledPartitionKind | None
    dirichlet_concentration: DirichletConcentration | None


def _declared_model_coefficients(training_model: TrainingModelId) -> tuple[ModelCoefficientValue | None, ...]:
    match training_model:
        case TrainingModelId.FEDPROX_AUTOENCODER:
            return tuple(ModelCoefficientValue(protocol.coefficient.value) for protocol in FEDPROX_TRAINING_PROTOCOLS)
        case TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            return tuple(ModelCoefficientValue(protocol.regularization.value) for protocol in DITTO_TRAINING_PROTOCOLS)
        case _:
            return (None,)


def _swept_cells(declaration: ExperimentDeclaration, seed_cohort: SeedCohort) -> tuple[_SweptCell, ...]:
    return tuple(
        _SweptCell(
            seed=seed,
            threshold_method=threshold_method,
            metric=metric,
            temporal_state=temporal_state,
            model_coefficient=model_coefficient,
            threshold_quantile=threshold_quantile,
            controlled_partition_kind=partition_kind,
            dirichlet_concentration=concentration,
        )
        for seed in seed_cohort.values
        for threshold_method in declaration.federated_thresholds
        for metric in declaration.metrics
        for temporal_state in _temporal_states(declaration.id)
        for model_coefficient in _declared_model_coefficients(declaration.training_model)
        for threshold_quantile in _threshold_quantiles(declaration.id)
        for partition_kind, concentration in _controlled_partition_cells(declaration)
    )


def _threshold_quantiles(experiment: ExperimentId) -> tuple[Quantile | None, ...]:
    if experiment is ExperimentId.QUANTILE_SENSITIVITY:
        return QUANTILE_GRID
    return (None,)


def _controlled_partition_cells(
    declaration: ExperimentDeclaration,
) -> tuple[tuple[ControlledPartitionKind | None, DirichletConcentration | None], ...]:
    if declaration.population is not PopulationId.NBAIOT_DIRICHLET_CLIENTS:
        return ((None, None),)
    dirichlet_cells = tuple(
        (ControlledPartitionKind.DIRICHLET, concentration) for concentration in DIRICHLET_CONCENTRATIONS
    )
    return (*dirichlet_cells, (ControlledPartitionKind.IID, None))


def _planned_entry(
    declaration: ExperimentDeclaration,
    cell: _SweptCell,
    evidence: tuple[PlanningEvidence, ...],
) -> PlannedExperiment:
    disposition, reason = _resolve_disposition(declaration, evidence)
    capabilities = population_capabilities(declaration.population)
    if cell.threshold_method not in capabilities.valid_threshold_methods:
        disposition = PlanDisposition.INFEASIBLE
        reason = "threshold_method_unsupported: population capability contract does not authorize this threshold method"
    population = population_declaration(declaration.population)
    return PlannedExperiment(
        coordinate=ExperimentCoordinate(
            experiment=declaration.id,
            evidence_role=declaration.role,
            dataset=population.dataset,
            population=declaration.population,
            training_model=declaration.training_model,
            training_seed=cell.seed,
            split_protocol=_coordinate_split_protocol(declaration.population, cell.temporal_state),
            preprocessing_protocol=declaration.preprocessing_protocol,
            model_coefficient=cell.model_coefficient,
            threshold_method=cell.threshold_method,
            metric=cell.metric,
            temporal_state=cell.temporal_state,
            threshold_quantile=cell.threshold_quantile,
            controlled_partition_kind=cell.controlled_partition_kind,
            dirichlet_concentration=cell.dirichlet_concentration,
        ),
        disposition=disposition,
        reason=reason,
    )


def _coordinate_split_protocol(
    population: PopulationId,
    temporal_state: TemporalState | None,
) -> SplitProtocolId:
    match temporal_state:
        case TemporalState.STATIC_REFERENCE:
            return SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
        case TemporalState.FROZEN_FUTURE | TemporalState.RECALIBRATED_FUTURE:
            return SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        case None:
            return split_protocol_for_population(population)


def _temporal_states(experiment: ExperimentId) -> tuple[TemporalState | None, ...]:
    matches = tuple(
        declaration.temporal_states
        for declaration in EXECUTION_IDENTITY_DECLARATIONS
        if declaration.experiment is experiment
    )
    if not matches:
        return (None,)
    if len(matches) != 1:
        raise ValueError("experiment temporal-state declaration must resolve exactly once")
    return matches[0]


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


def _digest_entries(entries: tuple[PlannedExperiment, ...]) -> Checksum:
    payload = "\n".join(f"{entry.coordinate.stable_key}|{entry.disposition.value}|{entry.reason}" for entry in entries)
    return checksum_text(payload)
