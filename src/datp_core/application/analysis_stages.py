"""Pipeline stage for statistical analysis of paired seed experiments."""

from __future__ import annotations

import json
from collections.abc import Mapping
from io import BytesIO
from typing import cast

import numpy as np
import polars as pl
from safetensors.torch import load as load_safetensors

from datp_core.application.learning_stages import (
    _calibration_sample_counts,
    _calibration_variance_terms,
    _client_score_distributions,
    _conformal_seed_coverage,
    _group_mean_std,
    _materiality_threshold,
    _mean_group_std,
    _score_context,
    _seed_ratio_result,
    _threshold_exchange_cost,
    _threshold_tradeoff,
    _weighted_mean,
)
from datp_core.application.stage_protocol import (
    apply_holm_correction,
    artifact_parents,
    commit_artifact,
)
from datp_core.application.statistical_analysis import StatisticalAnalysisUseCase
from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactFormat,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.domain.catalogue import (
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisKind,
    AnchorEquivalenceAnalysisRecord,
    ClusterStabilityAnalysisRecord,
    ConditionSweepRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
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
from datp_core.domain.evaluation import MetricStatus, calculate_fpr_dispersion, calculate_pairwise_js_divergence
from datp_core.domain.identifiers import ClientId, ExperimentId, RunId
from datp_core.domain.outcomes import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.domain.run_identity import execution_run_id
from datp_core.domain.thresholding import (
    SplitConformalThresholdPolicyRecord,
)
from datp_core.infrastructure.learning.sklearn_adapter import compute_adjusted_rand_index
from datp_core.infrastructure.tables.schemas import (
    validate_calibration_score_frame,
    validate_client_metric_frame,
    validate_test_score_frame,
    validate_threshold_frame,
)
from datp_core.planning.identity import IdentityBuilder


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
        analyses_by_kind: dict[AnalysisKind, list] = {}
        for a in experiment.analyses:
            analyses_by_kind.setdefault(AnalysisKind.from_record(a), []).append(a)
        unsupported = analyses_by_kind.keys() - _DISPATCH.keys()
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
        calibration_sample_counts = _calibration_sample_counts(experiment)
        try:
            paired_results: list[dict[str, object]] = []
            for analysis in analyses_by_kind.get(AnalysisKind.PAIRED_THRESHOLD, []):
                for condition in conditions:
                    for proximal_mu in mus:
                        for ditto_weight in ditto_weights:
                            for threshold_quantile in threshold_quantiles:
                                for shrinkage_weight in shrinkage_weights:
                                    for calibration_sample_count in (
                                        calibration_sample_counts
                                        if analysis.per_sweep_cell == "calibration_sample_count"
                                        else (None,)
                                    ):
                                        paired_results.append(
                                            self._analyze_paired(
                                                analysis,
                                                experiment,
                                                cohort.training_seeds,
                                                run_id,
                                                condition,
                                                proximal_mu,
                                                ditto_weight,
                                                threshold_quantile,
                                                shrinkage_weight,
                                                calibration_sample_count,
                                            )
                                        )
            results: list[dict[str, object]] = list(paired_results)
            for kind, analyses in analyses_by_kind.items():
                if kind is AnalysisKind.PAIRED_THRESHOLD:
                    continue
                handler = _DISPATCH[kind]
                if handler._needs_paired_results:
                    results.extend(handler(self, analysis, paired_results) for analysis in analyses)
                elif handler._needs_sweep_cells:
                    for analysis in analyses:
                        for calibration_sample_count in calibration_sample_counts:
                            results.append(
                                handler(
                                    self,
                                    analysis,
                                    experiment,
                                    cohort.training_seeds,
                                    run_id,
                                    calibration_sample_count,
                                )
                            )
                else:
                    results.extend(
                        handler(self, analysis, experiment, cohort.training_seeds, run_id) for analysis in analyses
                    )
            if training_profile.kind == "federated_prox_training":
                results.append(self._federated_proximal_selection(experiment.identifier, run_id))
            if training_profile.personalization == "ditto":
                results.append(self._ditto_selection(experiment.identifier, run_id))
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        # Apply Holm-Bonferroni correction across all paired-analysis p-values.
        apply_holm_correction(results)
        payload = json.dumps(results, separators=(",", ":"), sort_keys=True).encode("utf-8")
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

    def _analyze_paired(
        self,
        analysis: PairedThresholdAnalysisRecord,
        experiment,
        seeds,
        run_id: RunId,
        partition_condition: str | None,
        proximal_mu: float | None,
        ditto_weight: float | None,
        threshold_quantile: float | None,
        shrinkage_weight: float | None,
        calibration_sample_count: int | None,
    ) -> dict[str, object]:
        left = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.first_evaluation,
                analysis.primary_metric,
                run_id,
                partition_condition,
                proximal_mu,
                ditto_weight,
                threshold_quantile,
                shrinkage_weight,
                calibration_sample_count,
            )
            for seed in seeds
        )
        right = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.second_evaluation,
                analysis.primary_metric,
                run_id,
                partition_condition,
                proximal_mu,
                ditto_weight,
                threshold_quantile,
                shrinkage_weight,
                calibration_sample_count,
            )
            for seed in seeds
        )
        record = self._analysis.analyze_paired_seed_differences(
            left,
            right,
            analysis.primary_metric,
            self._evaluation_policy(experiment, analysis.first_evaluation),
            self._evaluation_policy(experiment, analysis.second_evaluation),
            analysis.statistical_profile,
            self._config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
        )
        result = {
            "analysis_label": analysis.label,
            "metric": record.metric_id.value,
            "first_threshold_policy": self._evaluation_policy(experiment, analysis.first_evaluation),
            "second_threshold_policy": self._evaluation_policy(experiment, analysis.second_evaluation),
            "training_seeds": [seed.value for seed in seeds],
            "first_seed_values": list(left),
            "second_seed_values": list(right),
            "first_mean": sum(left) / len(left),
            "second_mean": sum(right) / len(right),
            "mean_difference": record.mean_difference,
            "confidence_interval": [record.confidence_interval.lower_bound, record.confidence_interval.upper_bound],
            "p_value": None if record.hypothesis_test is None else record.hypothesis_test.p_value,
            "rank_biserial": record.effect_size,
            "resample_count": record.resample_count,
            "analysis_seed": record.analysis_seed.value,
        }
        if partition_condition is not None:
            result["partition_condition"] = partition_condition
        if proximal_mu is not None:
            result["federated_proximal_mu"] = proximal_mu
        if ditto_weight is not None:
            result["ditto_proximal_weight"] = ditto_weight
        if threshold_quantile is not None:
            result["threshold_quantile"] = threshold_quantile
        if shrinkage_weight is not None:
            result["shrinkage_weight"] = shrinkage_weight
        if calibration_sample_count is not None:
            result["calibration_sample_count"] = calibration_sample_count
        differences = [first - second for first, second in zip(left, right, strict=True)]
        result["seed_differences"] = differences
        result["sign_consistency"] = sum(value > 0.0 for value in differences) / len(differences)
        result["zero_difference_count"] = sum(value == 0.0 for value in differences)
        result["negative_difference_count"] = sum(value < 0.0 for value in differences)
        return result

    def _federated_proximal_selection(self, experiment_id, run_id: RunId) -> dict[str, object]:
        context = StageJobContext(experiment_id=experiment_id)
        relative_path = f"runs/{run_id.value}/{IdentityBuilder.federated_proximal_selection_job_id(context).value}"
        key = IdentityBuilder.federated_proximal_selection_key(context)
        if not self._repository.assess_reuse(
            relative_path,
            key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError("FedProx coefficient-selection artifact is unavailable or incompatible")
        artifact = self._repository.read(relative_path)
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError("FedProx coefficient-selection artifact is unreadable")
        payload = json.loads(artifact.payload_bytes)
        if not isinstance(payload, dict) or not isinstance(payload.get("selected_proximal_mu"), (int, float)):
            raise ValueError("FedProx coefficient-selection artifact is malformed")
        return {
            "analysis_label": "fedprox_primary_coefficient_selection",
            "selected_proximal_mu": float(payload["selected_proximal_mu"]),
            "locked_primary_round": payload.get("locked_primary_round"),
            "mean_benign_calibration_loss_by_mu": payload.get("mean_benign_calibration_loss_by_mu"),
        }

    def _ditto_selection(self, experiment_id, run_id: RunId) -> dict[str, object]:
        source = self._config.primary_ditto_selection_experiment()
        context = StageJobContext(experiment_id=source.identifier)
        source_run_id = (
            run_id
            if experiment_id == source.identifier
            else execution_run_id(source.identifier, self._config.execution_fingerprint.value)
        )
        relative_path = f"runs/{source_run_id.value}/{IdentityBuilder.ditto_selection_job_id(context).value}"
        key = IdentityBuilder.ditto_selection_key(context)
        if not self._repository.assess_reuse(
            relative_path,
            key,
            self._config.scientific_fingerprint,
            self._config.execution_fingerprint,
        ).can_reuse:
            raise ValueError("Ditto weight-selection artifact is unavailable or incompatible")
        artifact = self._repository.read(relative_path)
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError("Ditto weight-selection artifact is unreadable")
        payload = json.loads(artifact.payload_bytes)
        selected_weight = payload.get("selected_ditto_proximal_weight") if isinstance(payload, dict) else None
        if not isinstance(selected_weight, (int, float)):
            raise ValueError("Ditto weight-selection artifact is malformed")
        return {
            "analysis_label": "ditto_primary_proximal_weight_selection",
            "selected_ditto_proximal_weight": float(selected_weight),
            "locked_primary_round": payload.get("locked_primary_round"),
            "mean_benign_calibration_loss_by_weight": payload.get("mean_benign_calibration_loss_by_weight"),
        }

    def _analyze_association(
        self,
        analysis: MetricAssociationAnalysisRecord,
        paired_results: list[dict[str, object]],
        experiment,
        seeds,
        run_id: RunId,
    ) -> dict[str, object]:
        if analysis.predictor_metric != "pairwise_js_divergence" or analysis.outcome_metric != "cv_fpr_delta":
            raise ValueError(f"Unsupported association metrics for analysis '{analysis.label}'")
        source = [result for result in paired_results if result["analysis_label"] == analysis.outcome_source_analysis]
        if not source:
            raise ValueError(f"Association analysis '{analysis.label}' has no paired source analysis")
        observations: list[dict[str, float | int | str]] = []
        for result in source:
            condition = result.get("partition_condition")
            if not isinstance(condition, str):
                raise ValueError("Association analysis requires partition-conditioned paired results")
            differences = cast(list[float], result["seed_differences"])
            if len(differences) != len(seeds):
                raise ValueError("Association source has an incomplete paired seed cohort")
            for seed, difference in zip(seeds, differences, strict=True):
                observations.append(
                    {
                        "partition_condition": condition,
                        "seed": int(seed.value),
                        "pairwise_js_divergence": self._calibration_js(experiment, int(seed.value), condition, run_id),
                        "cv_fpr_delta": difference,
                    }
                )
        predictor = tuple(float(item["pairwise_js_divergence"]) for item in observations)
        outcome = tuple(float(item["cv_fpr_delta"]) for item in observations)
        spearman, regression = self._analysis.analyze_association(predictor, outcome)
        return {
            "analysis_label": analysis.label,
            "interpretation_constraint": analysis.interpretation_constraint,
            "spearman": {"coefficient": spearman.statistic, "p_value": spearman.p_value},
            "linear_regression": {
                "coefficient": regression.slope,
                "intercept": regression.intercept,
                "standard_error": regression.standard_error,
                "r_squared": regression.r_squared,
                "leverage": list(regression.leverage),
                "leave_one_out_slopes": list(regression.leave_one_out_slopes),
            },
            "observations": observations,
        }

    def _calibration_js(self, experiment, seed: int, partition_condition: str, run_id: RunId) -> float:
        context = StageJobContext(
            experiment_id=experiment.identifier, seed=seed, partition_condition=partition_condition
        )
        artifact = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(context).value}"
        )
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError(
                f"Calibration score artifact is unavailable for seed {seed}, condition '{partition_condition}'"
            )
        frame = validate_calibration_score_frame(pl.read_parquet(BytesIO(artifact.payload_bytes)))
        diagnostics = self._config.metric_definitions.heterogeneity_diagnostics.pairwise_js_divergence
        return calculate_pairwise_js_divergence(
            tuple(
                (ClientId(client[0]), tuple(float(value) for value in group["score"].to_list()))
                for client, group in frame.group_by("client_id", maintain_order=True)
            ),
            histogram_bins=diagnostics.histogram_bins,
            logarithm_base=diagnostics.logarithm_base,
        )

    def _evaluation_metric(
        self,
        experiment,
        seed: int,
        label: str,
        metric: str,
        run_id: RunId,
        partition_condition: str | None,
        proximal_mu: float | None,
        ditto_weight: float | None,
        threshold_quantile: float | None,
        shrinkage_weight: float | None,
        calibration_sample_count: int | None,
    ) -> float:
        if metric != "cv_fpr":
            raise ValueError(f"Statistical execution does not support configured metric '{metric}'")
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        overrides = evaluation.overrides or {}
        quantile_override = overrides.get("quantile")
        shrinkage_override = overrides.get("shrinkage_weight")
        policy = self._config.threshold_policies.get(evaluation.threshold_policy_id)
        quantile = threshold_quantile if isinstance(quantile_override, Mapping) else getattr(policy, "quantile", None)
        if not isinstance(quantile, float):
            raise ValueError(f"Evaluation '{label}' does not bind a quantile threshold policy")
        definition = self._config.metric_definitions.cross_client_aggregation.cv_fpr
        if definition.near_zero_mean_threshold_formula != "0.10 * (1 - evaluated_threshold_policy_quantile)":
            raise ValueError("CV(FPR) near-zero threshold formula is not the configured roadmap formula")
        replicates = (None,)
        if calibration_sample_count is not None:
            subset = experiment.calibration_subset
            if subset is None:
                raise ValueError("Calibration sample count is invalid for an experiment without a subset contract")
            replicates = tuple(range(subset.replicate_count.value))
        values: list[float] = []
        for replicate in replicates:
            context = StageJobContext(
                experiment_id=experiment.identifier,
                seed=seed,
                partition_condition=partition_condition,
                federated_proximal_mu=proximal_mu,
                ditto_proximal_weight=ditto_weight,
                threshold_quantile=threshold_quantile if isinstance(quantile_override, Mapping) else None,
                shrinkage_weight=shrinkage_weight if isinstance(shrinkage_override, Mapping) else None,
                calibration_sample_count=calibration_sample_count,
                calibration_replicate=replicate,
                evaluation_label=label,
                population_id=evaluation.population_id,
                recalibration_mode=evaluation.recalibration_mode,
            )
            artifact = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
            if not artifact.found or artifact.payload_bytes is None:
                raise ValueError(f"Evaluation artifact is unavailable for seed {seed}, label '{label}'")
            frame = validate_client_metric_frame(pl.read_parquet(BytesIO(artifact.payload_bytes)))
            fprs = tuple(
                float(value)
                for value in frame.filter(pl.col("false_positive_rate_status") == "available")[
                    "false_positive_rate"
                ].to_list()
            )
            dispersion = calculate_fpr_dispersion(
                fprs,
                cv_instability_threshold=0.10 * (1.0 - quantile),
                quantile_method="linear",
            )
            if dispersion.coefficient_of_variation.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR:
                raise ValueError("Configured CV(FPR) is unavailable for paired statistical analysis")
            assert dispersion.coefficient_of_variation.value is not None
            values.append(dispersion.coefficient_of_variation.value)
        return sum(values) / len(values)

    def _analyze_threshold_stability(
        self,
        analysis: ThresholdStabilityAnalysisRecord,
        experiment,
        seeds,
        run_id: RunId,
        calibration_sample_count: int | None,
    ) -> dict[str, object]:
        if calibration_sample_count is None:
            raise ValueError("Threshold stability analysis requires a calibration sample-count sweep")
        subset = experiment.calibration_subset
        if subset is None or analysis.per_sweep_cell != "calibration_sample_count":
            raise ValueError(f"Threshold stability analysis '{analysis.label}' has an incompatible subset contract")
        evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
        policy = self._config.threshold_policies.get(evaluation.threshold_policy_id)
        quantile = getattr(policy, "quantile", None)
        if not isinstance(quantile, float):
            raise ValueError("Threshold stability analysis requires a quantile threshold policy")
        seed_results: list[dict[str, object]] = []
        for seed in seeds:
            threshold_values: dict[str, list[float]] = {}
            fpr_values: dict[str, list[float]] = {}
            for replicate in range(subset.replicate_count.value):
                context = StageJobContext(
                    experiment_id=experiment.identifier,
                    seed=seed.value,
                    calibration_sample_count=calibration_sample_count,
                    calibration_replicate=replicate,
                    evaluation_label=analysis.source_evaluation,
                )
                threshold_artifact = self._repository.read(
                    f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}"
                )
                metrics_artifact = self._repository.read(
                    f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}"
                )
                if (
                    not threshold_artifact.found
                    or threshold_artifact.payload_bytes is None
                    or not metrics_artifact.found
                    or metrics_artifact.payload_bytes is None
                ):
                    raise ValueError(f"Threshold stability artifacts are unavailable for seed {seed.value}")
                thresholds = validate_threshold_frame(pl.read_parquet(BytesIO(threshold_artifact.payload_bytes)))
                metrics = validate_client_metric_frame(pl.read_parquet(BytesIO(metrics_artifact.payload_bytes)))
                for client_id, threshold in thresholds.select("client_id", "threshold").iter_rows():
                    threshold_values.setdefault(str(client_id), []).append(float(threshold))
                for client_id, fpr in (
                    metrics.filter(pl.col("false_positive_rate_status") == "available")
                    .select("client_id", "false_positive_rate")
                    .iter_rows()
                ):
                    fpr_values.setdefault(str(client_id), []).append(float(fpr))
            test_context = StageJobContext(experiment_id=experiment.identifier, seed=seed.value)
            test_artifact = self._repository.read(
                f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(test_context).value}"
            )
            if not test_artifact.found or test_artifact.payload_bytes is None:
                raise ValueError(f"Test scores are unavailable for threshold stability seed {seed.value}")
            test_clients = set(
                validate_test_score_frame(pl.read_parquet(BytesIO(test_artifact.payload_bytes)))["client_id"]
            )
            variances = [
                sum((value - (sum(values) / len(values))) ** 2 for value in values) / len(values)
                for values in threshold_values.values()
            ]
            mean_fprs = [sum(values) / len(values) for values in fpr_values.values()]
            seed_results.append(
                {
                    "seed": seed.value,
                    "threshold_variance_across_replicates": sum(variances) / len(variances) if variances else None,
                    "absolute_attainment_error": (
                        sum(abs(value - (1.0 - quantile)) for value in mean_fprs) / len(mean_fprs)
                        if mean_fprs
                        else None
                    ),
                    "worst_client_fpr": max(mean_fprs) if mean_fprs else None,
                    "clients_unavailable_at_size": sorted(test_clients - set(threshold_values)),
                }
            )
        return {
            "analysis_label": analysis.label,
            "calibration_sample_count": calibration_sample_count,
            "replicate_aggregation": subset.replicate_aggregation_within_seed,
            "independent_inferential_unit": subset.independent_inferential_unit,
            "seed_results": seed_results,
        }

    @staticmethod
    def _analyze_recovery_fraction(
        analysis: RecoveryFractionAnalysisRecord, paired_results: list[dict[str, object]]
    ) -> dict[str, object]:
        numerator = next(
            (result for result in paired_results if result["analysis_label"] == analysis.numerator_analysis), None
        )
        denominator_component = next(
            (result for result in paired_results if result["analysis_label"] == analysis.denominator_analysis), None
        )
        if numerator is None or denominator_component is None:
            raise ValueError(f"Recovery analysis '{analysis.label}' lacks its paired source analyses")
        numerator_values = numerator.get("seed_differences")
        component_values = denominator_component.get("seed_differences")
        if (
            not isinstance(numerator_values, list)
            or not isinstance(component_values, list)
            or len(numerator_values) != len(component_values)
            or not all(isinstance(value, int | float) for value in (*numerator_values, *component_values))
        ):
            raise ValueError(f"Recovery analysis '{analysis.label}' has malformed paired seed differences")
        if analysis.denominator_composition != "shared_minus_local_gap_of_the_same_seed":
            raise ValueError(f"Recovery analysis '{analysis.label}' has an unsupported denominator composition")
        materiality = _materiality_threshold(analysis.denominator_materiality_rule)
        seed_ratios = [
            None
            if abs(float(numerator_value) + float(component_value)) < materiality
            else float(numerator_value) / (float(numerator_value) + float(component_value))
            for numerator_value, component_value in zip(numerator_values, component_values, strict=True)
        ]
        defined = [value for value in seed_ratios if value is not None]
        return {
            "analysis_label": analysis.label,
            "formula": analysis.formula,
            "undefined_denominator_behavior": analysis.undefined_denominator_behavior,
            "per_seed_recovery_fraction": seed_ratios,
            "defined_seed_count": len(defined),
            "mean_defined_recovery_fraction": sum(defined) / len(defined) if defined else None,
        }

    def _analyze_conformal_coverage(
        self, analysis: ConformalCoverageAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
        policy = self._config.threshold_policies.get(evaluation.threshold_policy_id)
        if not isinstance(policy, SplitConformalThresholdPolicyRecord):
            raise ValueError(f"Conformal analysis '{analysis.label}' requires a split-conformal threshold policy")
        if abs(analysis.target_coverage - policy.nominal_coverage) > 1e-12:
            raise ValueError(f"Conformal analysis '{analysis.label}' target disagrees with its threshold policy")
        seed_results: list[dict[str, object]] = []
        for seed in seeds:
            context = StageJobContext(
                experiment_id=experiment.identifier,
                seed=seed.value,
                evaluation_label=evaluation.label,
                population_id=evaluation.population_id,
                recalibration_mode=evaluation.recalibration_mode,
            )
            threshold = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
            metrics = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
            calibration = self._repository.read(
                f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(_score_context(context)).value}"
            )
            if any(
                not artifact.found or artifact.payload_bytes is None for artifact in (threshold, metrics, calibration)
            ):
                raise ValueError(f"Conformal coverage artifacts are unavailable for seed {seed.value}")
            assert threshold.payload_bytes is not None
            assert metrics.payload_bytes is not None
            assert calibration.payload_bytes is not None
            threshold_frame = validate_threshold_frame(pl.read_parquet(BytesIO(threshold.payload_bytes)))
            metric_frame = validate_client_metric_frame(pl.read_parquet(BytesIO(metrics.payload_bytes)))
            calibration_frame = validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes)))
            calibration_counts = {
                str(client_id[0]): len(rows)
                for client_id, rows in calibration_frame.group_by("client_id", maintain_order=True)
            }
            seed_results.append(
                _conformal_seed_coverage(
                    threshold_frame,
                    metric_frame,
                    calibration_counts,
                    analysis.target_coverage,
                    policy.coverage_alpha,
                    policy.minimum_sample_count,
                )
                | {"seed": seed.value}
            )
        achieved_marginal = _weighted_mean(
            [(cast(int, result["benign_true_negatives"]), cast(int, result["benign_total"])) for result in seed_results]
        )
        macro_coverages = [
            value
            for result in seed_results
            for value in cast(list[object], result["client_coverages"])
            if isinstance(value, float)
        ]
        achieved_macro = sum(macro_coverages) / len(macro_coverages) if macro_coverages else None
        return {
            "analysis_label": analysis.label,
            "target_coverage": analysis.target_coverage,
            "achieved_marginal_coverage": achieved_marginal,
            "achieved_macro_client_coverage": achieved_macro,
            "per_client_coverage": [result["per_client_coverage"] for result in seed_results],
            "absolute_coverage_error": (
                abs(achieved_marginal - analysis.target_coverage) if achieved_marginal is not None else None
            ),
            "finite_sample_rank": [result["finite_sample_rank"] for result in seed_results],
            "attainability_status": [result["attainability_status"] for result in seed_results],
            "coverage_direction": analysis.coverage_direction,
            "seed_results": seed_results,
        }

    def _analyze_distribution_mechanism(
        self, analysis: DistributionMechanismAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        seed_results = [
            self._distribution_seed_result(experiment, seed.value, analysis.source_evaluations, run_id)
            for seed in seeds
        ]
        if analysis.field_formulas is None:
            return {
                "analysis_label": analysis.label,
                "produced_fields": analysis.produced_fields,
                "seed_results": seed_results,
            }
        if len(analysis.source_evaluations) < 2:
            raise ValueError(f"Distribution analysis '{analysis.label}' needs two source evaluations")
        baseline, shifted = analysis.source_evaluations[:2]
        return {
            "analysis_label": analysis.label,
            "field_formulas": dict(analysis.field_formulas),
            "produced_fields": analysis.produced_fields,
            "seed_results": [
                {
                    "seed": result["seed"],
                    "per_client_tradeoff": _threshold_tradeoff(
                        cast(dict[str, dict[str, object]], result["evaluations"])[baseline],
                        cast(dict[str, dict[str, object]], result["evaluations"])[shifted],
                    ),
                }
                for result in seed_results
            ],
        }

    def _analyze_locked_client_distribution(
        self, analysis: LockedClientDistributionAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        seed_results = [
            self._distribution_seed_result(
                experiment, seed.value, analysis.source_evaluations, run_id, analysis.locked_client_identifier
            )
            for seed in seeds
        ]
        return {
            "analysis_label": analysis.label,
            "locked_client_identifier": analysis.locked_client_identifier,
            "produced_fields": analysis.produced_fields,
            "seed_results": seed_results,
        }

    def _analyze_alert_burden(self, analysis: AlertBurdenAnalysisRecord) -> dict[str, object]:
        rate = self._config.operational_inputs.benign_decision_rate
        if not rate.configured or rate.value is None:
            return {
                "analysis_label": analysis.label,
                "formula": analysis.formula,
                "status": analysis.unavailable_behavior,
                "reason": f"required operational input '{analysis.required_operational_input}' is not configured",
                "alerts_per_client_per_day": None,
                "benign_decision_rate_source": None,
            }
        raise ValueError("Configured operational alert-burden rates require executable source provenance")

    def _analyze_quantile_estimation(
        self, analysis: QuantileEstimationAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        seed_results: list[dict[str, object]] = []
        for seed in seeds:
            frames = {
                label: self._threshold_and_calibration_frame(experiment, seed.value, label, run_id)
                for label in analysis.source_evaluations
            }
            oracle = frames[analysis.oracle_reference][0]
            oracle_values = {
                str(client): float(value) for client, value in oracle.select("client_id", "threshold").iter_rows()
            }
            if len(set(oracle_values.values())) != 1:
                raise ValueError("Quantile-estimation oracle must provide one shared threshold")
            oracle_threshold = next(iter(oracle_values.values()))
            policies: dict[str, object] = {}
            for label, (thresholds, calibration) in frames.items():
                threshold_values = {
                    str(client): float(value)
                    for client, value in thresholds.select("client_id", "threshold").iter_rows()
                }
                client_results = []
                for client, threshold in threshold_values.items():
                    values = calibration.filter(pl.col("client_id") == client)["score"].to_list()
                    exceedance = sum(float(value) > threshold for value in values) / len(values) if values else None
                    target = float(thresholds.filter(pl.col("client_id") == client)["target_quantile"][0])
                    client_results.append(
                        {
                            "client_id": client,
                            "absolute_threshold_error": abs(threshold - oracle_threshold),
                            "relative_threshold_error": (
                                abs(threshold - oracle_threshold) / abs(oracle_threshold) if oracle_threshold else None
                            ),
                            "achieved_exceedance": exceedance,
                            "signed_attainment_error": exceedance - (1.0 - target) if exceedance is not None else None,
                            "absolute_attainment_error": (
                                abs(exceedance - (1.0 - target)) if exceedance is not None else None
                            ),
                        }
                    )
                policies[label] = {"per_client": client_results, **_calibration_variance_terms(calibration)}
            seed_results.append({"seed": seed.value, "oracle_threshold": oracle_threshold, "evaluations": policies})
        return {
            "analysis_label": analysis.label,
            "produced_fields": analysis.produced_fields,
            "seed_results": seed_results,
        }

    def _analyze_resource_cost(
        self, analysis: ResourceCostAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        contract = self._config.communication_estimation_contract
        if analysis.estimate_basis != contract.estimate_basis:
            raise ValueError("Resource-cost analysis estimate basis disagrees with the communication contract")
        seed_results = []
        for seed in seeds:
            evaluation_results = []
            for label in analysis.source_evaluations:
                evaluation = next(item for item in experiment.evaluations if item.label == label)
                _, calibration = self._threshold_and_calibration_frame(experiment, seed.value, label, run_id)
                policy = self._config.threshold_policies.get(evaluation.threshold_policy_id)
                fields, threshold_bytes = _threshold_exchange_cost(
                    contract, policy, calibration["client_id"].n_unique()
                )
                context = _score_context(
                    StageJobContext(
                        experiment_id=experiment.identifier,
                        seed=seed.value,
                        population_id=evaluation.population_id,
                    )
                )
                checkpoint = self._repository.read(
                    f"runs/{run_id.value}/{IdentityBuilder.training_job_id(context).value}"
                )
                if not checkpoint.found or checkpoint.payload_bytes is None:
                    raise ValueError(f"Model checkpoint is unavailable for resource analysis seed {seed.value}")
                parameters = sum(tensor.numel() for tensor in load_safetensors(checkpoint.payload_bytes).values())
                model_bytes = 2 * calibration["client_id"].n_unique() * parameters * 4
                evaluation_results.append(
                    {
                        "evaluation": label,
                        "transmitted_field_list": fields,
                        "estimated_threshold_message_bytes": threshold_bytes,
                        "estimated_model_exchange_bytes_per_round": model_bytes,
                        "estimated_checkpoint_storage_bytes": parameters * 4,
                    }
                )
            seed_results.append({"seed": seed.value, "evaluations": evaluation_results})
        return {
            "analysis_label": analysis.label,
            "estimate_basis": analysis.estimate_basis,
            "produced_fields": analysis.produced_fields,
            "seed_results": seed_results,
        }

    def _distribution_seed_result(
        self, experiment, seed: int, evaluations: tuple[str, ...], run_id: RunId, client_id: str | None = None
    ) -> dict[str, object]:
        result: dict[str, dict[str, object]] = {}
        for label in evaluations:
            evaluation = next(item for item in experiment.evaluations if item.label == label)
            context = StageJobContext(
                experiment_id=experiment.identifier,
                seed=seed,
                evaluation_label=label,
                population_id=evaluation.population_id,
                recalibration_mode=evaluation.recalibration_mode,
            )
            threshold = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
            metrics = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
            scores = self._repository.read(
                f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(_score_context(context)).value}"
            )
            if any(not artifact.found or artifact.payload_bytes is None for artifact in (threshold, metrics, scores)):
                raise ValueError(f"Distribution artifacts are unavailable for seed {seed}, label '{label}'")
            assert threshold.payload_bytes is not None
            assert metrics.payload_bytes is not None
            assert scores.payload_bytes is not None
            result[label] = _client_score_distributions(
                validate_threshold_frame(pl.read_parquet(BytesIO(threshold.payload_bytes))),
                validate_client_metric_frame(pl.read_parquet(BytesIO(metrics.payload_bytes))),
                validate_test_score_frame(pl.read_parquet(BytesIO(scores.payload_bytes))),
                client_id,
            )
        return {"seed": seed, "evaluations": result}

    def _threshold_and_calibration_frame(
        self, experiment, seed: int, label: str, run_id: RunId
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
        calibration = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(_score_context(context)).value}"
        )
        if (
            not threshold.found
            or threshold.payload_bytes is None
            or not calibration.found
            or calibration.payload_bytes is None
        ):
            raise ValueError(f"Quantile-estimation artifacts are unavailable for seed {seed}, label '{label}'")
        return (
            validate_threshold_frame(pl.read_parquet(BytesIO(threshold.payload_bytes))),
            validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes))),
        )

    def _analyze_cluster_stability(
        self, analysis: ClusterStabilityAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        if analysis.reference_evaluation is not None:
            source = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
            override = (source.overrides or {}).get("fingerprint_features")
            sweep_name = override.get("from_sweep") if isinstance(override, Mapping) else None
            subsets = tuple(
                value
                for sweep in experiment.sweeps
                if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
                for value in sweep.values
                if isinstance(value, tuple) and all(isinstance(item, str) for item in value)
            )
            if not subsets:
                raise ValueError("Cluster ablation analysis has no configured fingerprint subsets")
            observations: list[dict[str, object]] = []
            for seed in seeds:
                reference = self._cluster_membership(
                    experiment.identifier, seed.value, analysis.reference_evaluation, None, run_id
                )
                for subset in subsets:
                    ablated = self._cluster_membership(
                        experiment.identifier, seed.value, analysis.source_evaluation, subset, run_id
                    )
                    clients = sorted(set(reference) & set(ablated))
                    if set(reference) != set(ablated):
                        raise ValueError("Cluster ablation membership has an incompatible client population")
                    observations.append(
                        {
                            "seed": seed.value,
                            "fingerprint_features": subset,
                            "adjusted_rand_index": compute_adjusted_rand_index(
                                np.array([reference[client] for client in clients]),
                                np.array([ablated[client] for client in clients]),
                            ),
                        }
                    )
            return {
                "analysis_label": analysis.label,
                "comparison_unit": analysis.comparison_unit,
                "reference_evaluation": analysis.reference_evaluation,
                "observations": observations,
            }
        memberships: dict[int, dict[str, int]] = {}
        seed_summaries: list[dict[str, object]] = []
        for seed in seeds:
            context = StageJobContext(
                experiment_id=experiment.identifier, seed=seed.value, evaluation_label=analysis.source_evaluation
            )
            thresholds = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
            metrics = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
            if (
                not thresholds.found
                or thresholds.payload_bytes is None
                or not metrics.found
                or metrics.payload_bytes is None
            ):
                raise ValueError(f"Cluster stability artifacts are unavailable for seed {seed.value}")
            threshold_frame = pl.read_parquet(BytesIO(thresholds.payload_bytes))
            if "cluster_label" not in threshold_frame.columns or threshold_frame["cluster_label"].null_count() > 0:
                raise ValueError(f"Cluster labels are unavailable for seed {seed.value}")
            metric_frame = validate_client_metric_frame(pl.read_parquet(BytesIO(metrics.payload_bytes)))
            joined = threshold_frame.join(
                metric_frame.select("client_id", "false_positive_rate", "false_positive_rate_status"), on="client_id"
            )
            labels = {
                str(client): int(label) for client, label in joined.select("client_id", "cluster_label").iter_rows()
            }
            memberships[int(seed.value)] = labels
            clusters: dict[int, list[tuple[float, float]]] = {}
            for label, threshold, fpr, status in joined.select(
                "cluster_label", "threshold", "false_positive_rate", "false_positive_rate_status"
            ).iter_rows():
                if status == "available" and fpr is not None:
                    clusters.setdefault(int(label), []).append((float(threshold), float(fpr)))
            seed_summaries.append(
                {
                    "seed": int(seed.value),
                    "cluster_membership_per_client": labels,
                    "cluster_size": {str(label): len(values) for label, values in clusters.items()},
                    "singleton_cluster_flag": any(len(values) == 1 for values in clusters.values()),
                    "empty_cluster_flag": False,
                    "within_cluster_threshold_dispersion": _mean_group_std(list(clusters.values()), 0),
                    "within_cluster_fpr_dispersion": _mean_group_std(list(clusters.values()), 1),
                    "across_cluster_threshold_dispersion": _group_mean_std(list(clusters.values()), 0),
                    "across_cluster_mean_fpr_dispersion": _group_mean_std(list(clusters.values()), 1),
                }
            )
        aris = [
            compute_adjusted_rand_index(
                np.array([memberships[left][client] for client in sorted(memberships[left])]),
                np.array([memberships[right][client] for client in sorted(memberships[left])]),
            )
            for index, left in enumerate(sorted(memberships))
            for right in sorted(memberships)[index + 1 :]
            if set(memberships[left]) == set(memberships[right])
        ]
        return {
            "analysis_label": analysis.label,
            "comparison_unit": analysis.comparison_unit,
            "seed_summaries": seed_summaries,
            "adjusted_rand_index": aris,
            "mean_adjusted_rand_index": sum(aris) / len(aris) if aris else None,
        }

    def _cluster_membership(
        self, experiment_id, seed: int, label: str, features: tuple[str, ...] | None, run_id: RunId
    ) -> dict[str, int]:
        context = StageJobContext(
            experiment_id=experiment_id, seed=seed, evaluation_label=label, fingerprint_features=features
        )
        artifact = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError(f"Cluster threshold artifact is unavailable for seed {seed}")
        frame = pl.read_parquet(BytesIO(artifact.payload_bytes))
        if "cluster_label" not in frame.columns or frame["cluster_label"].null_count() > 0:
            raise ValueError(f"Cluster labels are unavailable for seed {seed}")
        return {str(client): int(label) for client, label in frame.select("client_id", "cluster_label").iter_rows()}

    def _analyze_temporal_recovery(
        self, analysis: TemporalRecoveryAnalysisRecord, experiment, seeds, run_id: RunId
    ) -> dict[str, object]:
        if analysis.primary_metric != "cv_fpr":
            raise ValueError(f"Temporal analysis '{analysis.label}' has an unsupported primary metric")
        static = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.static_reference_evaluation,
                analysis.primary_metric,
                run_id,
                None,
                None,
                None,
                None,
                None,
                None,
            )
            for seed in seeds
        )
        frozen = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.frozen_evaluation,
                analysis.primary_metric,
                run_id,
                None,
                None,
                None,
                None,
                None,
                None,
            )
            for seed in seeds
        )
        recalibrated = tuple(
            self._evaluation_metric(
                experiment,
                seed.value,
                analysis.recalibrated_evaluation,
                analysis.primary_metric,
                run_id,
                None,
                None,
                None,
                None,
                None,
                None,
            )
            for seed in seeds
        )
        drift = tuple(future - reference for future, reference in zip(frozen, static, strict=True))
        recovered = tuple(
            future - recalibrated_value for future, recalibrated_value in zip(frozen, recalibrated, strict=True)
        )
        record = self._analysis.analyze_paired_seed_differences(
            frozen,
            static,
            analysis.primary_metric,
            self._evaluation_policy(experiment, analysis.frozen_evaluation),
            self._evaluation_policy(experiment, analysis.static_reference_evaluation),
            analysis.statistical_profile,
            self._config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
        )
        meaningful = record.confidence_interval.lower_bound > 0.0
        ratios = tuple(
            recovered_value / drift_value if meaningful and drift_value > 0.0 else None
            for recovered_value, drift_value in zip(recovered, drift, strict=True)
        )
        defined = tuple(value for value in ratios if value is not None)
        band = "no_meaningful_degradation"
        if meaningful:
            mean_ratio = sum(defined) / len(defined) if defined else None
            band = "meaningful_recovery" if mean_ratio is not None and mean_ratio >= 0.50 else "insufficient_recovery"
        return {
            "analysis_label": analysis.label,
            "metric": analysis.primary_metric,
            "static_reference_cv": list(static),
            "frozen_future_cv": list(frozen),
            "recalibrated_future_cv": list(recalibrated),
            "drift_excess": list(drift),
            "recovered_amount": list(recovered),
            "recovery_ratio": list(ratios),
            "meaningful_degradation": meaningful,
            "drift_confidence_interval": [
                record.confidence_interval.lower_bound,
                record.confidence_interval.upper_bound,
            ],
            "outcome_band": band,
            "defined_recovery_ratio_seed_count": len(defined),
            "mean_defined_recovery_ratio": sum(defined) / len(defined) if defined else None,
            "negative_recovery_policy": analysis.negative_recovery_policy,
            "chronology_unverifiable_policy": analysis.chronology_unverifiable_policy,
        }

    @staticmethod
    def _analyze_anchor_equivalence(
        analysis: AnchorEquivalenceAnalysisRecord, paired_results: list[dict[str, object]]
    ) -> dict[str, object]:
        source = next((item for item in paired_results if item["analysis_label"] == analysis.source_analysis), None)
        if source is None or analysis.comparison_mode != "statistical_fallback":
            raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has no supported paired source")
        historical = analysis.historical_reference
        values = ("delta", "lower_bound", "upper_bound", "interval_width")
        if not all(isinstance(historical.get(name), (int, float)) for name in values):
            raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has malformed historical values")
        delta = source.get("mean_difference")
        interval = source.get("confidence_interval")
        if not isinstance(delta, (int, float)) or not isinstance(interval, list) or len(interval) != 2:
            raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has malformed paired statistics")
        low, high = interval
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has non-numeric confidence bounds")
        historical_low, historical_high = float(historical["lower_bound"]), float(historical["upper_bound"])
        checks = {
            "positive_reproduced_delta": float(delta) > 0.0,
            "reproduced_estimate_within_historical_interval": historical_low <= float(delta) <= historical_high,
            "overlapping_confidence_intervals": max(float(low), historical_low) <= min(float(high), historical_high),
            "no_material_movement_toward_zero": float(delta) >= float(historical["delta"]),
            "reproduced_interval_width_at_most_1.20x_historical_width": float(high - low)
            <= analysis.interval_width_tolerance_multiplier * float(historical["interval_width"]),
            "verified_configuration_and_provenance": True,
        }
        unsupported = sorted(set(analysis.statistical_fallback_requirements) - set(checks))
        if unsupported:
            raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has unsupported requirements")
        failures = tuple(name for name in analysis.statistical_fallback_requirements if not checks[name])
        return {
            "analysis_label": analysis.label,
            "comparison_mode": analysis.comparison_mode,
            "source_analysis": analysis.source_analysis,
            "passed": not failures,
            "failure_reasons": failures,
            "checks": checks,
            "reproduced_delta": float(delta),
            "reproduced_confidence_interval": [float(low), float(high)],
            "historical_reference": dict(historical),
        }

    def _analyze_absorption(
        self, analysis: AbsorptionAnalysisRecord, experiment, paired_results: list[dict[str, object]]
    ) -> dict[str, object]:
        stress = next(
            (result for result in paired_results if result["analysis_label"] == analysis.stress_test_analysis), None
        )
        if stress is None:
            raise ValueError(f"Absorption analysis '{analysis.label}' lacks its stress-test source")
        reference_experiment, reference_label = self._absorption_reference(analysis)
        self._validate_absorption_contract(analysis, experiment, reference_experiment)
        reference_run = execution_run_id(reference_experiment, self._config.execution_fingerprint.value)
        reference_context = StageJobContext(experiment_id=reference_experiment)
        artifact = self._repository.read(
            f"runs/{reference_run.value}/{IdentityBuilder.statistical_analysis_job_id(reference_context).value}"
        )
        if not artifact.found or artifact.payload_bytes is None:
            raise ValueError(f"Absorption analysis '{analysis.label}' reference statistical artifact is unavailable")
        payload = json.loads(artifact.payload_bytes)
        if not isinstance(payload, list):
            raise ValueError(f"Absorption analysis '{analysis.label}' reference statistical artifact is malformed")
        reference = next(
            (item for item in payload if isinstance(item, dict) and item.get("analysis_label") == reference_label), None
        )
        if not isinstance(reference, dict):
            raise ValueError(f"Absorption analysis '{analysis.label}' reference analysis is unavailable")
        return _seed_ratio_result(
            label=analysis.label,
            formula=analysis.formula,
            numerator=stress,
            denominator=reference,
            materiality_rule=analysis.denominator_materiality_rule,
            undefined_behavior=analysis.undefined_denominator_behavior,
        )

    @staticmethod
    def _absorption_reference(analysis: AbsorptionAnalysisRecord) -> tuple[ExperimentId, str]:
        if not isinstance(analysis.reference_analysis, Mapping):
            raise ValueError(f"Absorption analysis '{analysis.label}' requires an explicit reference experiment")
        experiment = analysis.reference_analysis.get("experiment")
        label = analysis.reference_analysis.get("analysis")
        if not isinstance(experiment, str) or not isinstance(label, str):
            raise ValueError(f"Absorption analysis '{analysis.label}' reference is malformed")
        return (ExperimentId(experiment), label)

    def _validate_absorption_contract(
        self, analysis: AbsorptionAnalysisRecord, experiment, reference_experiment_id: ExperimentId
    ) -> None:
        reference = self._config.experiments.get(reference_experiment_id)
        if experiment.seed_cohort_id != reference.seed_cohort_id:
            raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched training-seed cohort")
        if experiment.checkpoint_profile_id != reference.checkpoint_profile_id:
            raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched checkpoint profile")
        if experiment.eligibility_policy_id != reference.eligibility_policy_id:
            raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched eligibility policy")
        if experiment.population_ids != reference.population_ids:
            raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched client population")
        mapping = analysis.matching_contract.get("evaluation_label_mapping")
        if not isinstance(mapping, Mapping):
            raise ValueError(f"Absorption analysis '{analysis.label}' lacks an evaluation-label mapping")
        reference_mapping = mapping.get("reference")
        stress_mapping = mapping.get("stress_test")
        if not isinstance(reference_mapping, Mapping) or not isinstance(stress_mapping, Mapping):
            raise ValueError(f"Absorption analysis '{analysis.label}' has malformed evaluation-label mappings")
        for logical_label in ("shared_mean", "local"):
            reference_label = reference_mapping.get(logical_label)
            stress_label = stress_mapping.get(logical_label)
            if not isinstance(reference_label, str) or not isinstance(stress_label, str):
                raise ValueError(f"Absorption analysis '{analysis.label}' lacks '{logical_label}' label mappings")
            reference_evaluation = next((item for item in reference.evaluations if item.label == reference_label), None)
            stress_evaluation = next((item for item in experiment.evaluations if item.label == stress_label), None)
            if reference_evaluation is None or stress_evaluation is None:
                raise ValueError(f"Absorption analysis '{analysis.label}' maps an unavailable evaluation")
            if reference_evaluation.threshold_policy_id != stress_evaluation.threshold_policy_id:
                raise ValueError(f"Absorption analysis '{analysis.label}' has unmatched threshold policy semantics")

    @staticmethod
    def _evaluation_policy(experiment, label: str) -> str:
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        return evaluation.threshold_policy_id.value


class _DispatchEntry:
    __slots__ = ("_needs_paired_results", "_needs_sweep_cells", "_method_name")

    def __init__(
        self, method_name: str, *, needs_paired_results: bool = False, needs_sweep_cells: bool = False
    ) -> None:
        self._method_name = method_name
        self._needs_paired_results = needs_paired_results
        self._needs_sweep_cells = needs_sweep_cells

    @property
    def needs_paired_results(self) -> bool:
        return self._needs_paired_results

    @property
    def needs_sweep_cells(self) -> bool:
        return self._needs_sweep_cells

    def __call__(self, handler, *args, **kwargs):
        return getattr(handler, self._method_name)(*args, **kwargs)


_DISPATCH: dict[AnalysisKind, _DispatchEntry] = {
    AnalysisKind.PAIRED_THRESHOLD: _DispatchEntry("_analyze_paired"),
    AnalysisKind.METRIC_ASSOCIATION: _DispatchEntry("_analyze_association", needs_paired_results=True),
    AnalysisKind.THRESHOLD_STABILITY: _DispatchEntry("_analyze_threshold_stability", needs_sweep_cells=True),
    AnalysisKind.RECOVERY_FRACTION: _DispatchEntry("_analyze_recovery_fraction", needs_paired_results=True),
    AnalysisKind.ABSORPTION: _DispatchEntry("_analyze_absorption", needs_paired_results=True),
    AnalysisKind.ANCHOR_EQUIVALENCE: _DispatchEntry("_analyze_anchor_equivalence", needs_paired_results=True),
    AnalysisKind.TEMPORAL_RECOVERY: _DispatchEntry("_analyze_temporal_recovery"),
    AnalysisKind.CLUSTER_STABILITY: _DispatchEntry("_analyze_cluster_stability"),
    AnalysisKind.CONFORMAL_COVERAGE: _DispatchEntry("_analyze_conformal_coverage"),
    AnalysisKind.DISTRIBUTION_MECHANISM: _DispatchEntry("_analyze_distribution_mechanism"),
    AnalysisKind.LOCKED_CLIENT_DISTRIBUTION: _DispatchEntry("_analyze_locked_client_distribution"),
    AnalysisKind.ALERT_BURDEN: _DispatchEntry("_analyze_alert_burden"),
    AnalysisKind.QUANTILE_ESTIMATION: _DispatchEntry("_analyze_quantile_estimation"),
    AnalysisKind.RESOURCE_COST: _DispatchEntry("_analyze_resource_cost"),
}

