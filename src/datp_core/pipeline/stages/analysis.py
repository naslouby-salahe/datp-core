"""Statistical-analysis pipeline stage handler."""

from __future__ import annotations

from collections.abc import Sequence

from datp_core.analysis.contracts import AnalysisResultContract
from datp_core.analysis.errors import AnalysisError
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository, _ArtifactPathIndex
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.persistence import persist_analysis_results
from datp_core.analysis.runtime.planning import expand_paired_analysis_cells, resolve_sweep_dimensions
from datp_core.analysis.runtime.runner import AnalysisRunner
from datp_core.analysis.selection import ditto_selection, federated_proximal_selection
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase, apply_holm_correction
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId, SeedCohortId, TrainingProfileId
from datp_core.core.seeding import Seed
from datp_core.experiments import PairedThresholdAnalysisRecord
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
        exp_id = ExperimentId(job.context.experiment_id)
        experiment = self._config.experiments.get(exp_id)
        cohort = self._config.seed_cohorts.get(SeedCohortId(experiment.seed_cohort_id))
        training_profile = self._config.training_profiles.get(TrainingProfileId(experiment.training_profile_id))

        try:
            path_index = _ArtifactPathIndex.from_stage_inputs(job.inputs)
            artifacts = AnalysisArtifactRepository(store=self._store, path_index=path_index)

            context = AnalysisExecutionContext(
                config=self._config,
                artifacts=artifacts,
                experiment=experiment,
                seeds=tuple(Seed(s) for s in cohort.training_seeds),
                statistical_analysis=self._analysis,
            )
            runner = AnalysisRunner(context=context)
            dimensions = resolve_sweep_dimensions(experiment, training_profile)

            results_list: list[AnalysisResultContract] = []
            for analysis_record in experiment.analyses:
                if isinstance(analysis_record, PairedThresholdAnalysisRecord):
                    cells = expand_paired_analysis_cells(analysis_record, dimensions)
                    for cell in cells:
                        results_list.extend(runner.run(analysis_record, cell=cell))
                else:
                    results_list.extend(runner.run(analysis_record))

            sel_ctx = context.selection_context(context.seeds[0])
            if training_profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
                selection_payload = artifacts.checkpoint_selection(sel_ctx)
                results_list.append(federated_proximal_selection(selection_payload))

            if training_profile.personalization == PersonalizationStrategy.DITTO:
                selection_payload = artifacts.checkpoint_selection(sel_ctx)
                results_list.append(ditto_selection(selection_payload))

            finalized: Sequence[AnalysisResultContract] = apply_holm_correction(results_list)
            persist_analysis_results(store=self._store, job=job, results=finalized)

        except AnalysisError as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
