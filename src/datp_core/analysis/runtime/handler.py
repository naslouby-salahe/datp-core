"""Statistical-analysis pipeline stage handler.

Builds an ``AnalysisExecutionContext``, dispatches analysis records through the
typed runner, applies Holm correction, and persists results.
"""

from __future__ import annotations

from datp_core.analysis.errors import AnalysisError
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.persistence import persist_analysis_results
from datp_core.analysis.runtime.planning import expand_paired_analysis_cells, resolve_sweep_dimensions
from datp_core.analysis.runtime.runner import AnalysisRunner
from datp_core.analysis.selection import ditto_selection, federated_proximal_selection
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase, apply_holm_correction
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.learning.contracts.enums import PersonalizationStrategy, TrainingProfileKind
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class StatisticalAnalysisStageHandler:
    """Pipeline stage handler for statistical analysis."""

    stage = StageKind.STATISTICAL_ANALYSIS

    def __init__(
        self, config: ResolvedProjectConfiguration, store: ArtifactStore, analysis: StatisticalAnalysisUseCase
    ) -> None:
        self._config = config
        self._store = store
        self._analysis = analysis

    def execute(self, job: StageJob) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        training_profile = self._config.training_profiles.get(experiment.training_profile_id)

        artifacts = AnalysisArtifactRepository(self._store)
        context = AnalysisExecutionContext(
            config=self._config,
            artifacts=artifacts,
            experiment=experiment,
            seeds=cohort.training_seeds,
        )
        runner = AnalysisRunner(context=context)
        dimensions = resolve_sweep_dimensions(experiment, training_profile)

        try:
            results: list = []
            for analysis_record in experiment.analyses:
                kind = analysis_record.kind
                if kind == "paired_threshold_analysis":
                    from datp_core.experiments import PairedThresholdAnalysisRecord

                    if isinstance(analysis_record, PairedThresholdAnalysisRecord):
                        cells = expand_paired_analysis_cells(analysis_record, dimensions)
                        for cell in cells:
                            results.extend(runner.run(analysis_record, cell=cell))
                else:
                    results.extend(runner.run(analysis_record))

            if training_profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
                checkpoint_bytes = self._store.read_bytes(
                    self._resolve_checkpoint_selection_path(job)
                )
                results.append(federated_proximal_selection(checkpoint_bytes))
            if training_profile.personalization == PersonalizationStrategy.DITTO:
                checkpoint_bytes = self._store.read_bytes(
                    self._resolve_checkpoint_selection_path(job)
                )
                results.append(ditto_selection(checkpoint_bytes))

        except AnalysisError as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        try:
            finalized = apply_holm_correction(results)
            persist_analysis_results(store=self._store, job=job, results=finalized)
        except AnalysisError as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)

    @staticmethod
    def _resolve_checkpoint_selection_path(job: StageJob) -> str:
        for item in job.inputs:
            if item.coordinates and item.coordinates.output_name == "checkpoint_selection":
                return item.relative_path
        return ""
