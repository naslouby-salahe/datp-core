"""Freeze the planner-supplied statistical result and evaluation provenance."""

from __future__ import annotations

from datp_core.artifacts.provenance import git_revision
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.reporting.freezing.errors import ResultFreezeError
from datp_core.reporting.freezing.service import freeze_result_family


class ResultFreezeStageHandler:
    stage = StageKind.RESULT_FREEZE

    def __init__(self, config: ResolvedProjectConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        try:
            experiment = self._config.experiments.get(job.context.experiment_id)
            profiles = tuple(self._config.report_profiles.get(identifier) for identifier in experiment.report_ids)
            cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
            population = (
                self._config.populations.get(experiment.population_ids[0]) if experiment.population_ids else None
            )
            source_files = [(job.input_path("statistical_result"), "statistical_result")]
            source_files.extend(
                (item.relative_path, "client_metrics")
                for item in job.inputs
                if item.name.startswith("client_metrics_")
            )
            payload = freeze_result_family(
                experiment=experiment,
                report_profiles=profiles,
                statistical_summary=self._store.read_bytes(job.input_path("statistical_result")),
                source_files=source_files,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_revision=git_revision(),
                seed_count=len(cohort.training_seeds),
                dataset_id=population.dataset_id.value if population is not None else None,
            )
            self._store.write_bytes_atomic(job.output_path("frozen_result"), payload)
        except (KeyError, OSError, ResultFreezeError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
