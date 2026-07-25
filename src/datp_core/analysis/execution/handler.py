"""Statistical-analysis pipeline stage handler: reuse check, per-analysis-kind grouping, typed
sweep-cell expansion, dispatch to capability implementations, and outcome conversion only. Sweep
expansion lives in ``execution/plan.py``, dispatch in ``execution/dispatch.py``, and Holm
correction/serialization/commit in ``execution/persistence.py``.
"""

from __future__ import annotations

from datp_core.analysis.artifact_access.reader import read_artifact_bytes
from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.execution.dispatch import dispatch, dispatch_paired
from datp_core.analysis.execution.inputs import AnalysisInputBundle, PrerequisiteExperimentResult
from datp_core.analysis.execution.persistence import persist_analysis_results
from datp_core.analysis.execution.plan import SweepDimensions, expand_paired_analysis_cells, resolve_sweep_dimensions
from datp_core.analysis.result import AnalysisResult
from datp_core.analysis.selection.training_parameters import ditto_selection, federated_proximal_selection
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.core.seeding import Seed
from datp_core.experiments import AnalysisKind, AnalysisRecord, ExperimentRecord, PairedThresholdAnalysisRecord
from datp_core.learning.contracts.enums import PersonalizationStrategy, TrainingProfileKind
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.reporting.freezing.codec import decode_manifest


class StatisticalAnalysisStageHandler:
    """Persist configured paired seed analyses from immutable evaluation artifacts."""

    stage = StageKind.STATISTICAL_ANALYSIS

    def __init__(
        self, config: ResolvedProjectConfiguration, store: ArtifactStore, analysis: StatisticalAnalysisUseCase
    ) -> None:
        self._config = config
        self._store = store
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
        inputs = AnalysisInputBundle.from_stage_inputs(job.inputs)
        try:
            paired_results = tuple(
                result
                for analysis_record in analyses_by_kind.get(AnalysisKind.PAIRED_THRESHOLD, [])
                for result in self._dispatch_paired(
                    analysis_record, dimensions, experiment, cohort.training_seeds, inputs
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
                            store=self._store,
                            inputs=inputs,
                            statistical_analysis=self._analysis,
                            experiment=experiment,
                            seeds=cohort.training_seeds,
                            paired_results=paired_results,
                            prerequisite_results=self._prerequisite_results(job),
                            calibration_sample_count_values=dimensions.calibration_sample_count_values,
                        )
                    )
            if training_profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
                results.append(
                    federated_proximal_selection(
                        read_artifact_bytes(
                            self._store,
                            inputs.checkpoint_selection(job.context),
                            missing_message="FedProx coefficient-selection input is unavailable",
                        )
                    )
                )
            if training_profile.personalization == PersonalizationStrategy.DITTO:
                results.append(
                    ditto_selection(
                        read_artifact_bytes(
                            self._store,
                            inputs.checkpoint_selection(job.context),
                            missing_message="Ditto weight-selection input is unavailable",
                        )
                    )
                )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        try:
            persist_analysis_results(store=self._store, job=job, results=results)
        except ValueError as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)

    def _dispatch_paired(
        self,
        analysis_record: AnalysisRecord,
        dimensions: SweepDimensions,
        experiment: ExperimentRecord,
        seeds: tuple[Seed, ...],
        inputs: AnalysisInputBundle,
    ) -> tuple[PairedThresholdAnalysisResult, ...]:
        assert isinstance(analysis_record, PairedThresholdAnalysisRecord)
        cells = expand_paired_analysis_cells(analysis_record, dimensions)
        return dispatch_paired(
            analysis_record,
            cells,
            config=self._config,
            store=self._store,
            inputs=inputs,
            statistical_analysis=self._analysis,
            experiment=experiment,
            seeds=seeds,
        )

    def _prerequisite_results(self, job: StageJob) -> tuple[PrerequisiteExperimentResult, ...]:
        declared = [
            item for item in job.inputs if item.name.startswith("prerequisite_frozen_result_")
        ]
        if job.context.prerequisite_results and declared:
            raise ValueError("Analysis job has both planned and preloaded prerequisite results")
        if job.context.prerequisite_results:
            return job.context.prerequisite_results
        results: list[PrerequisiteExperimentResult] = []
        for item in declared:
            frozen = decode_manifest(self._store.read_bytes(item.relative_path))
            results.append(
                PrerequisiteExperimentResult(
                    experiment_id=ExperimentId(frozen.experiment_id),
                    frozen_result_path=item.relative_path,
                    frozen_result_checksum=self._store.checksum(item.relative_path).value,
                    scientific_fingerprint=frozen.scientific_fingerprint,
                    result=frozen,
                )
            )
        return tuple(results)


__all__ = ["StatisticalAnalysisStageHandler"]
