"""Planning and execution records, isolated from configuration parsing."""

from __future__ import annotations

from dataclasses import dataclass

from ..catalogue.domain import ExperimentDefinition
from ..kernel.fingerprints import Fingerprint
from ..kernel.ids import ExperimentId, JobId, RunId
from ..kernel.values import StructuredValue


@dataclass(frozen=True, slots=True, kw_only=True)
class SweepCoordinate:
    components: tuple[tuple[str, StructuredValue], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedPlan:
    training_seed: int
    bootstrap_analysis_seed: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificRun:
    run_id: RunId
    experiment_id: ExperimentId
    coordinate: SweepCoordinate
    seed_plan: SeedPlan
    scientific_fingerprint: Fingerprint


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentPlan:
    experiment: ExperimentDefinition
    coordinates: tuple[SweepCoordinate, ...]
    runs: tuple[ScientificRun, ...]
    dependency_ids: tuple[ExperimentId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionJob:
    job_id: JobId
    stage: str
    parent_job_ids: tuple[JobId, ...]
    expected_artifact_key: Fingerprint


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionPlan:
    experiment_plan: ExperimentPlan
    jobs: tuple[ExecutionJob, ...]
    plan_fingerprint: Fingerprint
