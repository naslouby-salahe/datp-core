"""Threshold-estimator protocol, configured dispatch across all 12 policy families, the
construction use case, and the threshold-construction pipeline stage.

`ConfiguredThresholdEstimator.estimate()` dispatches to the family-group modules
(quantiles.py, grouped.py, conformal.py, shrinkage_and_federated.py) rather than embedding all 12
families' math in one place -- the estimator-layer mirror of the same 12-family mixing previously
duplicated across the authored schema and resolver layers (see CURRENT_ARCHITECTURE.md §9.3).
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Protocol, runtime_checkable

import polars as pl
from attrs import define, evolve

from datp_core.artifacts.models import (
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.sweeps import score_context
from datp_core.pipeline.frames import validate_calibration_score_frame, validate_threshold_frame
from datp_core.pipeline.identifiers import ClientId, PopulationId, RunId, ThresholdPolicyId
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact
from datp_core.pipeline.values import Seed, TypedDomainRegistry
from datp_core.thresholding.conformal import estimate_conformal
from datp_core.thresholding.grouped import estimate_cluster
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    CalibrationFallbackThresholdPolicyRecord,
    CentralizedPooledThresholdPolicyRecord,
    ClusterThresholdPolicyRecord,
    FamilyMeanThresholdPolicyRecord,
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    SplitConformalThresholdPolicyRecord,
    ThresholdPolicyRecord,
    ThresholdSet,
    policy_quantile,
    quantile,
)
from datp_core.thresholding.quantiles import (
    estimate_family_mean,
    estimate_local_quantile,
    estimate_pooled,
    estimate_shared_mean,
    estimate_shared_weighted,
)
from datp_core.thresholding.shrinkage_and_federated import (
    estimate_calibration_fallback,
    estimate_federated_fixed,
    estimate_federated_matched,
    estimate_shrinkage,
)


@define(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionRequest:
    """Request payload containing calibration scores and the resolved domain policy record."""

    policy_id: ThresholdPolicyId
    policy: ThresholdPolicyRecord
    calibration: tuple[BenignCalibrationScores, ...]
    population_id: PopulationId
    family_map: dict[str, str] | None = None
    seed: Seed | None = None
    selected_coefficient: float | None = None


@runtime_checkable
class ThresholdEstimator(Protocol):
    """Protocol for a threshold policy estimator."""

    @property
    def policy_id(self) -> ThresholdPolicyId: ...

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet: ...


class ConfiguredThresholdEstimator(ThresholdEstimator):
    """One immutable estimator bound to a single resolved policy configuration."""

    def __init__(self, policy_id: ThresholdPolicyId, policy: ThresholdPolicyRecord) -> None:
        self._policy_id = policy_id
        self._policy = policy

    @property
    def policy_id(self) -> ThresholdPolicyId:
        return self._policy_id

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        if request.policy_id != self._policy_id or type(request.policy) is not type(self._policy):
            raise ValueError("Threshold estimator request does not match its resolved policy kind")
        calibration = request.calibration
        if not calibration:
            raise ValueError("Threshold construction requires at least one eligible client")
        policy = request.policy
        target_quantile = policy_quantile(policy)
        local = {item.client_id.value: quantile(item.values, target_quantile.value) for item in calibration}

        if isinstance(policy, SharedMeanThresholdPolicyRecord):
            return estimate_shared_mean(self._policy_id, calibration, local, target_quantile)
        if isinstance(policy, (SharedPooledThresholdPolicyRecord, CentralizedPooledThresholdPolicyRecord)):
            return estimate_pooled(self._policy_id, calibration, local, target_quantile, quantile)
        if isinstance(policy, SharedWeightedThresholdPolicyRecord):
            return estimate_shared_weighted(self._policy_id, calibration, local, target_quantile)
        if isinstance(policy, LocalQuantileThresholdPolicyRecord):
            return estimate_local_quantile(self._policy_id, calibration, local, target_quantile)
        if isinstance(policy, FamilyMeanThresholdPolicyRecord):
            return estimate_family_mean(self._policy_id, calibration, local, target_quantile, request.family_map)
        if isinstance(policy, ClusterThresholdPolicyRecord):
            return estimate_cluster(self._policy_id, calibration, local, target_quantile, policy, quantile)
        if isinstance(policy, SplitConformalThresholdPolicyRecord):
            return estimate_conformal(self._policy_id, calibration, target_quantile, policy)
        if isinstance(policy, LocalGlobalShrinkageThresholdPolicyRecord):
            coefficient = (
                policy.shrinkage_weight if policy.shrinkage_weight is not None else request.selected_coefficient
            )
            if coefficient is None:
                raise ValueError("Shrinkage threshold requires an experiment-selected coefficient")
            return estimate_shrinkage(self._policy_id, calibration, local, target_quantile, coefficient)
        if isinstance(policy, CalibrationFallbackThresholdPolicyRecord):
            return estimate_calibration_fallback(self._policy_id, calibration, local, target_quantile, policy)
        if isinstance(policy, FederatedMatchedExceedanceThresholdPolicyRecord):
            return estimate_federated_matched(self._policy_id, calibration, target_quantile, policy)
        if isinstance(policy, FederatedFixedCoefficientThresholdPolicyRecord):
            coefficient = policy.fixed_k if policy.fixed_k is not None else request.selected_coefficient
            if coefficient is None:
                raise ValueError("Fixed-k threshold requires an experiment-selected coefficient")
            return estimate_federated_fixed(self._policy_id, calibration, target_quantile, coefficient)
        raise TypeError(f"Unsupported threshold policy configuration: {type(policy).__name__}")


class ConstructThresholdsUseCase:
    """Construct threshold sets using estimators injected by the composition root.

    The estimator registry is built from infrastructure implementations in the
    composition root; this use case only depends on the Protocol, not any
    concrete estimator class.
    """

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        registry: TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator],
    ) -> None:
        self._config = config
        self._registry = registry

    def execute(
        self,
        policy_id: ThresholdPolicyId,
        calibration: tuple[BenignCalibrationScores, ...],
        population_id: PopulationId,
        family_map: dict[str, str] | None,
        seed: Seed | None,
        selected_coefficient: float | None,
        quantile_override: float | None = None,
        fingerprint_features_override: tuple[str, ...] | None = None,
    ) -> ThresholdSet:
        estimator = self._registry.get(policy_id)
        policy = self._config.threshold_policies.get(policy_id)
        if quantile_override is not None:
            if not 0.0 < quantile_override < 1.0 or not hasattr(policy, "quantile"):
                raise ValueError("Threshold quantile override is invalid for the configured policy")
            policy = evolve(policy, quantile=quantile_override)
        if fingerprint_features_override is not None:
            if (
                not isinstance(policy, ClusterThresholdPolicyRecord)
                or not fingerprint_features_override
                or any(feature not in policy.fingerprint_features for feature in fingerprint_features_override)
            ):
                raise ValueError("Fingerprint-feature override is invalid for the configured cluster policy")
            policy = evolve(policy, fingerprint_features=fingerprint_features_override)
        return estimator.estimate(
            ThresholdConstructionRequest(
                policy_id=policy_id,
                policy=policy,
                calibration=calibration,
                population_id=population_id,
                family_map=family_map,
                seed=seed,
                selected_coefficient=selected_coefficient,
            )
        )


class ThresholdConstructionStageHandler:
    """Construct one configured threshold set from immutable benign calibration scores."""

    stage = StageKind.THRESHOLD_CONSTRUCTION

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        repository: ArtifactRepository,
        thresholds: ConstructThresholdsUseCase,
    ) -> None:
        self._config = config
        self._repository = repository
        self._thresholds = thresholds

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        if job.context.threshold_policy_id is None or job.context.population_id is None or job.context.seed is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Threshold construction requires policy, population, and seed",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        calibration_context = score_context(
            job.context, retain_calibration_subset=job.context.calibration_sample_count is not None
        )
        if calibration_context.calibration_sample_count is not None:
            calibration_job_id = IdentityBuilder.calibration_subset_job_id(calibration_context)
        elif job.context.recalibration_mode == "one_shot":
            calibration_job_id = IdentityBuilder.future_recalibration_score_job_id(calibration_context)
        else:
            calibration_job_id = IdentityBuilder.calibration_score_job_id(calibration_context)
        calibration = self._repository.read(f"runs/{run_id.value}/{calibration_job_id.value}")
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        experiment = self._config.experiments.get(job.context.experiment_id)
        population = self._config.populations.get(job.context.population_id)
        dataset = self._config.datasets[population.dataset_id]
        evaluation = next((item for item in experiment.evaluations if item.label == job.context.evaluation_label), None)
        if evaluation is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Evaluation configuration is unavailable"
            )
        if (
            evaluation.overrides
            and job.context.threshold_quantile is None
            and job.context.shrinkage_weight is None
            and job.context.federated_summary_fixed_k is None
            and job.context.fingerprint_features is None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Sweep-derived threshold overrides require explicit expanded jobs",
            )
        try:
            scores = pl.read_parquet(BytesIO(calibration.payload_bytes))
            validate_calibration_score_frame(scores)
            threshold_set: ThresholdSet | None = None
            if scores.is_empty():
                output = pl.DataFrame(
                    schema={
                        "client_id": pl.String,
                        "threshold": pl.Float64,
                        "owner_kind": pl.String,
                        "effective_lambda": pl.Float64,
                        "cluster_label": pl.Int64,
                        "finite_sample_rank": pl.Int64,
                        "attainability_status": pl.String,
                        "policy_id": pl.String,
                        "target_quantile": pl.Float64,
                    }
                )
            else:
                grouped = tuple(
                    BenignCalibrationScores(
                        client_id=ClientId(str(client_id[0])),
                        values=tuple(float(value) for value in rows["score"].to_list()),
                        population_id=job.context.population_id,
                    )
                    for client_id, rows in scores.group_by("client_id", maintain_order=True)
                )
                threshold_set = self._thresholds.execute(
                    job.context.threshold_policy_id,
                    grouped,
                    job.context.population_id,
                    dict(dataset.field_schema.label_fields.family_map)
                    if dataset.field_schema.label_fields.family_map
                    else None,
                    Seed(job.context.seed),
                    (
                        job.context.shrinkage_weight
                        if job.context.shrinkage_weight is not None
                        else job.context.federated_summary_fixed_k
                    ),
                    job.context.threshold_quantile,
                    job.context.fingerprint_features,
                )
                output = pl.DataFrame(
                    {
                        "client_id": [record.client_id.value for record in threshold_set.values],
                        "threshold": [float(record.threshold) for record in threshold_set.values],
                        "owner_kind": [record.owner for record in threshold_set.values],
                        "effective_lambda": [record.effective_lambda for record in threshold_set.values],
                        "cluster_label": [record.cluster_label for record in threshold_set.values],
                        "finite_sample_rank": [record.finite_sample_rank for record in threshold_set.values],
                        "attainability_status": [
                            None if record.attainability_status is None else record.attainability_status.value
                            for record in threshold_set.values
                        ],
                        "policy_id": [threshold_set.policy_id.value] * len(threshold_set.values),
                        "target_quantile": [threshold_set.target_quantile.value] * len(threshold_set.values),
                    },
                    schema_overrides={
                        "effective_lambda": pl.Float64,
                        "cluster_label": pl.Int64,
                        "finite_sample_rank": pl.Int64,
                        "attainability_status": pl.String,
                    },
                )
            validate_threshold_frame(output)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        output.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "threshold artifact commit failed",
            )
        if threshold_set is not None and threshold_set.diagnostics:
            diagnostics_key = ArtifactKey(
                artifact_id=ArtifactId(f"{job.output.artifact_id.value}:diagnostics"),
                kind=ArtifactKind.THRESHOLD_DIAGNOSTICS,
            )
            diagnostics_relative = f"{relative_path}.diagnostics"
            diagnostics_payload = json.dumps(threshold_set.diagnostics, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
            diagnostics_commit = commit_artifact(
                self._repository,
                self._config,
                job.context,
                artifact_key=diagnostics_key,
                artifact_format=ArtifactFormat.JSON,
                relative_path=diagnostics_relative,
                parents=artifact_parents(self._config, (job.output,)),
                payload=BytesPayload(payload_bytes=diagnostics_payload),
            )
            if not diagnostics_commit.success:
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message=diagnostics_commit.error_message or "threshold diagnostics commit failed",
                )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
