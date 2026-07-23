"""Statistical-analysis pipeline stage: orchestrates the per-analysis-family dispatch across
``analysis/{paired,association,stability,coverage,temporal,resources,distributions}.py`` and
persists the typed result list as a JSON artifact.

Two genuine dispatch bugs were found and fixed while migrating this handler out of the untyped
``application/analysis_stages.py``: the pre-refactor generic ``_DISPATCH`` table called
``_analyze_association``/``_analyze_absorption`` with too few positional arguments and
``_analyze_alert_burden`` with too many, which would have raised ``TypeError`` at runtime for any
experiment actually configuring one of those three analysis kinds (evidently never exercised).
Typing each family function's real parameter list here makes that class of bug a Pyright error
instead of a runtime one, so the fix is enforced by the type checker going forward.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import cast

from attrs import evolve

from datp_core.analysis.association import analyze_association
from datp_core.analysis.coverage import analyze_absorption, analyze_conformal_coverage, analyze_recovery_fraction
from datp_core.analysis.distributions import analyze_distribution_mechanism, analyze_locked_client_distribution, analyze_quantile_estimation
from datp_core.analysis.models import (
    AnalysisResult,
    PairedThresholdAnalysisResult,
    StatisticalAnalysisUseCase,
    analysis_result_to_payload,
    holm_adjust_p_values,
)
from datp_core.analysis.paired import analyze_anchor_equivalence, analyze_paired, ditto_selection, federated_proximal_selection
from datp_core.analysis.resources import analyze_alert_burden, analyze_resource_cost
from datp_core.analysis.stability import analyze_cluster_stability, analyze_threshold_stability
from datp_core.analysis.temporal import analyze_temporal_recovery
from datp_core.artifacts.models import ArtifactFormat, ArtifactRepository, BytesPayload
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.experiments.models import (
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisKind,
    AnalysisRecord,
    AnchorEquivalenceAnalysisRecord,
    ClusterStabilityAnalysisRecord,
    ConditionSweepRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    ExperimentRecord,
    LockedClientDistributionAnalysisRecord,
    MetricAssociationAnalysisRecord,
    PairedThresholdAnalysisRecord,
    QuantileEstimationAnalysisRecord,
    RecoveryFractionAnalysisRecord,
    ResourceCostAnalysisRecord,
    TemporalRecoveryAnalysisRecord,
    ThresholdStabilityAnalysisRecord,
    ValueSweepRecord,
)
from datp_core.experiments.sweeps import calibration_sample_counts
from datp_core.pipeline.identifiers import RunId
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact
from datp_core.pipeline.values import Seed


def apply_holm_correction(results: list[AnalysisResult]) -> list[AnalysisResult]:
    """Apply the Holm-Bonferroni correction across every paired-threshold analysis' p-value."""
    candidates: list[tuple[int, float]] = [
        (index, result.p_value)
        for index, result in enumerate(results)
        if isinstance(result, PairedThresholdAnalysisResult) and result.p_value is not None
    ]
    if len(candidates) < 2:
        return results
    adjusted = holm_adjust_p_values(value for _, value in candidates)
    updated = list(results)
    for (index, _), adjusted_value in zip(candidates, adjusted, strict=True):
        updated[index] = evolve(cast(PairedThresholdAnalysisResult, updated[index]), holm_adjusted_p_value=adjusted_value)
    return updated


class StatisticalAnalysisStageHandler:
    """Persist configured paired seed analyses from immutable evaluation artifacts."""

    stage = StageKind.STATISTICAL_ANALYSIS

    def __init__(
        self, config: ResolvedProjectConfiguration, repository: ArtifactRepository, analysis: StatisticalAnalysisUseCase
    ) -> None:
        self._config = config
        self._repository = repository
        self._analysis = analysis

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        experiment = self._config.experiments.get(job.context.experiment_id)
        analyses_by_kind: dict[AnalysisKind, list[AnalysisRecord]] = {}
        for analysis_record in experiment.analyses:
            analyses_by_kind.setdefault(AnalysisKind.from_record(analysis_record), []).append(analysis_record)
        unsupported = analyses_by_kind.keys() - set(AnalysisKind)
        if unsupported:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=f"Statistical handler does not yet support: {sorted(k.value for k in unsupported)}",
            )
        cohort = self._config.seed_cohorts.get(experiment.seed_cohort_id)
        conditions = tuple(
            condition.name
            for sweep in experiment.sweeps
            if isinstance(sweep, ConditionSweepRecord)
            for condition in sweep.conditions
        ) or (None,)
        mu_sweep = experiment.training_overrides.get("mu") if experiment.training_overrides is not None else None
        mu_sweep_name = mu_sweep.get("from_sweep") if isinstance(mu_sweep, Mapping) else None
        mus = tuple(
            float(value)
            for sweep in experiment.sweeps
            if isinstance(sweep, ValueSweepRecord) and sweep.name == mu_sweep_name
            for value in sweep.values
            if isinstance(value, float)
        ) or (None,)
        training_profile = self._config.training_profiles.get(experiment.training_profile_id)
        ditto_weights = (
            training_profile.personalization_parameter_grid or (None,)
            if training_profile.personalization == "ditto"
            else (None,)
        )
        threshold_quantiles = tuple(
            float(value)
            for sweep in experiment.sweeps
            if isinstance(sweep, ValueSweepRecord) and sweep.name == "threshold_quantile"
            for value in sweep.values
            if isinstance(value, float)
        ) or (None,)
        shrinkage_weights = tuple(
            float(value)
            for sweep in experiment.sweeps
            if isinstance(sweep, ValueSweepRecord) and sweep.name == "shrinkage_weight"
            for value in sweep.values
            if isinstance(value, float)
        ) or (None,)
        calibration_sample_count_values = calibration_sample_counts(experiment)
        try:
            paired_results = self._analyze_all_paired(
                analyses_by_kind.get(AnalysisKind.PAIRED_THRESHOLD, []),
                experiment=experiment,
                seeds=cohort.training_seeds,
                run_id=run_id,
                conditions=conditions,
                mus=mus,
                ditto_weights=ditto_weights,
                threshold_quantiles=threshold_quantiles,
                shrinkage_weights=shrinkage_weights,
                calibration_sample_count_values=calibration_sample_count_values,
            )
            results: list[AnalysisResult] = list(paired_results)
            for kind, analyses in analyses_by_kind.items():
                if kind is AnalysisKind.PAIRED_THRESHOLD:
                    continue
                for analysis_record in analyses:
                    results.extend(
                        self._dispatch(
                            kind,
                            analysis_record,
                            experiment=experiment,
                            seeds=cohort.training_seeds,
                            run_id=run_id,
                            paired_results=paired_results,
                            calibration_sample_count_values=calibration_sample_count_values,
                        )
                    )
            if training_profile.kind == "federated_prox_training":
                results.append(
                    federated_proximal_selection(
                        experiment.identifier, config=self._config, repository=self._repository, run_id=run_id
                    )
                )
            if training_profile.personalization == "ditto":
                results.append(
                    ditto_selection(experiment.identifier, config=self._config, repository=self._repository, run_id=run_id)
                )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        corrected = apply_holm_correction(results)
        payload = json.dumps(
            [analysis_result_to_payload(result) for result in corrected], separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.JSON,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "statistical artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)

    def _analyze_all_paired(
        self,
        analyses: list[AnalysisRecord],
        *,
        experiment: ExperimentRecord,
        seeds: tuple[Seed, ...],
        run_id: RunId,
        conditions: tuple[str | None, ...],
        mus: tuple[float | None, ...],
        ditto_weights: tuple[float | None, ...],
        threshold_quantiles: tuple[float | None, ...],
        shrinkage_weights: tuple[float | None, ...],
        calibration_sample_count_values: tuple[int | None, ...],
    ) -> tuple[PairedThresholdAnalysisResult, ...]:
        paired_results: list[PairedThresholdAnalysisResult] = []
        for analysis_record in analyses:
            assert isinstance(analysis_record, PairedThresholdAnalysisRecord)
            for condition in conditions:
                for proximal_mu in mus:
                    for ditto_weight in ditto_weights:
                        for threshold_quantile in threshold_quantiles:
                            for shrinkage_weight in shrinkage_weights:
                                for calibration_sample_count in (
                                    calibration_sample_count_values
                                    if analysis_record.per_sweep_cell == "calibration_sample_count"
                                    else (None,)
                                ):
                                    paired_results.append(
                                        analyze_paired(
                                            analysis_record,
                                            config=self._config,
                                            repository=self._repository,
                                            statistical_analysis=self._analysis,
                                            experiment=experiment,
                                            seeds=seeds,
                                            run_id=run_id,
                                            partition_condition=condition,
                                            proximal_mu=proximal_mu,
                                            ditto_weight=ditto_weight,
                                            threshold_quantile=threshold_quantile,
                                            shrinkage_weight=shrinkage_weight,
                                            calibration_sample_count=calibration_sample_count,
                                        )
                                    )
        return tuple(paired_results)

    def _dispatch(
        self,
        kind: AnalysisKind,
        analysis_record: AnalysisRecord,
        *,
        experiment: ExperimentRecord,
        seeds: tuple[Seed, ...],
        run_id: RunId,
        paired_results: tuple[PairedThresholdAnalysisResult, ...],
        calibration_sample_count_values: tuple[int | None, ...],
    ) -> list[AnalysisResult]:
        config, repository, statistical_analysis = self._config, self._repository, self._analysis
        match kind:
            case AnalysisKind.METRIC_ASSOCIATION:
                assert isinstance(analysis_record, MetricAssociationAnalysisRecord)
                return [
                    analyze_association(
                        analysis_record,
                        paired_results,
                        config=config,
                        repository=repository,
                        statistical_analysis=statistical_analysis,
                        experiment=experiment,
                        seeds=tuple(seed.value for seed in seeds),
                        run_id=run_id,
                    )
                ]
            case AnalysisKind.THRESHOLD_STABILITY:
                assert isinstance(analysis_record, ThresholdStabilityAnalysisRecord)
                return [
                    analyze_threshold_stability(
                        analysis_record,
                        config=config,
                        repository=repository,
                        experiment=experiment,
                        seeds=seeds,
                        run_id=run_id,
                        calibration_sample_count=calibration_sample_count,
                    )
                    for calibration_sample_count in calibration_sample_count_values
                ]
            case AnalysisKind.RECOVERY_FRACTION:
                assert isinstance(analysis_record, RecoveryFractionAnalysisRecord)
                return [analyze_recovery_fraction(analysis_record, paired_results)]
            case AnalysisKind.ABSORPTION:
                assert isinstance(analysis_record, AbsorptionAnalysisRecord)
                return [analyze_absorption(analysis_record, experiment, paired_results, config=config, repository=repository)]
            case AnalysisKind.ANCHOR_EQUIVALENCE:
                assert isinstance(analysis_record, AnchorEquivalenceAnalysisRecord)
                return [analyze_anchor_equivalence(analysis_record, paired_results)]
            case AnalysisKind.TEMPORAL_RECOVERY:
                assert isinstance(analysis_record, TemporalRecoveryAnalysisRecord)
                return [
                    analyze_temporal_recovery(
                        analysis_record,
                        config=config,
                        repository=repository,
                        statistical_analysis=statistical_analysis,
                        experiment=experiment,
                        seeds=seeds,
                        run_id=run_id,
                    )
                ]
            case AnalysisKind.CLUSTER_STABILITY:
                assert isinstance(analysis_record, ClusterStabilityAnalysisRecord)
                return [
                    analyze_cluster_stability(
                        analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                    )
                ]
            case AnalysisKind.CONFORMAL_COVERAGE:
                assert isinstance(analysis_record, ConformalCoverageAnalysisRecord)
                return [
                    analyze_conformal_coverage(
                        analysis_record, config=config, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                    )
                ]
            case AnalysisKind.DISTRIBUTION_MECHANISM:
                assert isinstance(analysis_record, DistributionMechanismAnalysisRecord)
                return [
                    analyze_distribution_mechanism(
                        analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                    )
                ]
            case AnalysisKind.LOCKED_CLIENT_DISTRIBUTION:
                assert isinstance(analysis_record, LockedClientDistributionAnalysisRecord)
                return [
                    analyze_locked_client_distribution(
                        analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                    )
                ]
            case AnalysisKind.ALERT_BURDEN:
                assert isinstance(analysis_record, AlertBurdenAnalysisRecord)
                return [analyze_alert_burden(analysis_record, config=config)]
            case AnalysisKind.QUANTILE_ESTIMATION:
                assert isinstance(analysis_record, QuantileEstimationAnalysisRecord)
                return [
                    analyze_quantile_estimation(
                        analysis_record, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                    )
                ]
            case AnalysisKind.RESOURCE_COST:
                assert isinstance(analysis_record, ResourceCostAnalysisRecord)
                return [
                    analyze_resource_cost(
                        analysis_record, config=config, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
                    )
                ]
            case AnalysisKind.PAIRED_THRESHOLD:
                raise AssertionError("paired-threshold analyses are dispatched by _analyze_all_paired")


__all__ = ["StatisticalAnalysisStageHandler", "apply_holm_correction"]
