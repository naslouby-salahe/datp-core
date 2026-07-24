"""Statistical-analysis pipeline stage handler: reuse check, per-analysis-kind grouping, typed
sweep-cell expansion, dispatch to capability implementations, and outcome conversion only. Sweep
expansion lives in ``execution/plan.py``, dispatch in ``execution/dispatch.py``, and Holm
correction/serialization/commit in ``execution/persistence.py``.
"""

from __future__ import annotations

from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.execution.dispatch import dispatch, dispatch_paired
from datp_core.analysis.execution.persistence import persist_analysis_results
from datp_core.analysis.execution.plan import SweepDimensions, expand_paired_analysis_cells, resolve_sweep_dimensions
from datp_core.analysis.result import AnalysisResult
from datp_core.analysis.selection.training_parameters import ditto_selection, federated_proximal_selection
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.experiments import AnalysisKind, AnalysisRecord, ExperimentRecord, PairedThresholdAnalysisRecord
from datp_core.learning.contracts.enums import PersonalizationStrategy, TrainingProfileKind
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class StatisticalAnalysisStageHandler:
    """Persist configured paired seed analyses from immutable evaluation artifacts."""

    stage = StageKind.STATISTICAL_ANALYSIS

    def __init__(
        self, config: ResolvedProjectConfiguration, repository: ArtifactRepository, analysis: StatisticalAnalysisUseCase
    ) -> None:
        self._config = config
        self._repository = repository
        self._analysis = analysis

    def execute(self, job: StageJob) -> StageJobOutcome:
        experiment = self._config.experiments.get(job.context.experiment_id)
        analyses_by_kind: dict[AnalysisKind, list[AnalysisRecord]] = {}
        for analysis_record in experiment.analyses:
            analyses_by_kind.setdefault(AnalysisKind(analysis_record.kind), []).append(analysis_record)
        unsupported = analyses_by_kind.keys() - set(AnalysisKind)
        if unsupported:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Statistical handler does not yet support: {sorted(k.value for k in unsupported)}",
            )
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        training_profile = self._config.training_profiles.get(experiment.training_profile_id)
        dimensions = resolve_sweep_dimensions(experiment, training_profile)
        try:
            paired_results = tuple(
                result
                for analysis_record in analyses_by_kind.get(AnalysisKind.PAIRED_THRESHOLD, [])
                for result in self._dispatch_paired(
                    analysis_record, dimensions, experiment, cohort.training_seeds
                )
            )
            results: list[AnalysisResult] = list(paired_results)
            for kind, analyses in analyses_by_kind.items():
                if kind is AnalysisKind.PAIRED_THRESHOLD:
                    continue
                for analysis_record in analyses:
                    results.extend(
                        dispatch(
                            kind,
                            analysis_record,
                            config=self._config,
                            repository=self._repository,
                            statistical_analysis=self._analysis,
                            experiment=experiment,
                            seeds=cohort.training_seeds,
                            experiment_id=experiment.identifier,
                            paired_results=paired_results,
                            calibration_sample_count_values=dimensions.calibration_sample_count_values,
                        )
                    )
            if training_profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
                results.append(
                    federated_proximal_selection(
                        experiment.identifier, config=self._config, repository=self._repository
                    )
                )
            if training_profile.personalization == PersonalizationStrategy.DITTO:
                results.append(
                    ditto_selection(
                        experiment.identifier, config=self._config, repository=self._repository
                    )
                )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        commit = persist_analysis_results(
            repository=self._repository, config=self._config, job=job, experiment_id=experiment.identifier, results=results
        )
        if not commit.success:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=commit.error_message or "statistical artifact commit failed",
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_artifact=job.output)

    def _dispatch_paired(
        self,
        analysis_record: AnalysisRecord,
        dimensions: SweepDimensions,
        experiment: ExperimentRecord,
        seeds: tuple[Seed, ...],
    ) -> tuple[PairedThresholdAnalysisResult, ...]:
        assert isinstance(analysis_record, PairedThresholdAnalysisRecord)
        cells = expand_paired_analysis_cells(analysis_record, dimensions)
        return dispatch_paired(
            analysis_record,
            cells,
            config=self._config,
            repository=self._repository,
            statistical_analysis=self._analysis,
            experiment=experiment,
            seeds=seeds,
            experiment_id=experiment.identifier,
        )


__all__ = ["StatisticalAnalysisStageHandler"]
