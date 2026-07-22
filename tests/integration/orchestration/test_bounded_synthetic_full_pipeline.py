"""A bounded, fully synthetic run of the complete `anchor_reproduction` pipeline.

This is the single end-to-end proof that the real orchestrator (`ExecuteExperimentUseCase`,
the same code path `datp-core experiment run` uses) can drive a real experiment from dataset
materialization through report generation without any stage silently skipping, using real
training (a real 150-round CUDA run per seed on tiny synthetic data), real scoring, real
threshold construction (including the family and K=3 cluster policies, which require several
distinct, family-mapped clients), real operating-point evaluation, real statistical analysis,
real result freeze, and real report rendering -- then proves resumability by running the exact
same experiment a second time against the same artifact repository and asserting every job is
reused rather than recomputed.

Only dataset materialization is bypassed (the real adapters read from `data/raw/`, which this
test must not touch); a schema-correct synthetic materialized dataset is committed directly at
each seed's expected artifact path, exactly as `DatasetMaterializationStageHandler`'s own reuse
path would find it, so every stage downstream of materialization is exercised for real.
"""

from __future__ import annotations

import json
from io import BytesIO

import numpy as np
import polars as pl

from datp_core.application.experiment_execution import ExecuteExperimentUseCase
from datp_core.application.stage_handlers import (
    CalibrationSubsamplingStageHandler,
    CohortCheckpointSelectionStageHandler,
    DatasetMaterializationStageHandler,
    ModelTrainingStageHandler,
    OperatingPointEvaluationStageHandler,
    PreflightStageHandler,
    ReportGenerationStageHandler,
    ResultFreezeStageHandler,
    ScoreGenerationStageHandler,
    StatisticalAnalysisStageHandler,
    ThresholdConstructionStageHandler,
)
from datp_core.application.statistical_analysis import StatisticalAnalysisUseCase
from datp_core.application.threshold_construction import ConstructThresholdsUseCase
from datp_core.composition.root import _build_adapter_registry, _build_estimator_registry, build_application
from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    BytesPayload,
)
from datp_core.domain.identifiers import ExperimentId
from datp_core.domain.outcomes import JobExecutionStatus, StageKind
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository
from datp_core.infrastructure.statistics.scipy_adapter import ScipyStatisticalAnalysisAdapter

_EXPERIMENT_ID = ExperimentId("anchor_reproduction")
# Real N-BaIoT family_map entries (configs/datasets/nbaiot.yaml), spanning 3 distinct families,
# so both the family-mean (B3) and K=3-cluster (B4) evaluations are non-degenerate.
_CLIENTS = ("Danmini_Doorbell", "Ecobee_Thermostat", "Provision_PT_737E_Security_Camera")


def _build_executor(config, repository: AtomicArtifactRepository) -> ExecuteExperimentUseCase:
    """Mirrors composition/root.py:build_application's handler wiring against a test repository."""
    adapter_registry = _build_adapter_registry()
    construct_thresholds = ConstructThresholdsUseCase(config=config, registry=_build_estimator_registry(config))
    statistical_analysis = StatisticalAnalysisUseCase(ScipyStatisticalAnalysisAdapter(), config.statistical_profiles)
    return ExecuteExperimentUseCase(
        config=config,
        handlers=(
            PreflightStageHandler(config, repository),
            DatasetMaterializationStageHandler(config, repository, adapter_registry),
            ModelTrainingStageHandler(config, repository),
            CohortCheckpointSelectionStageHandler(config, repository),
            ScoreGenerationStageHandler(config, repository),
            CalibrationSubsamplingStageHandler(config, repository),
            ThresholdConstructionStageHandler(config, repository, construct_thresholds),
            OperatingPointEvaluationStageHandler(config, repository),
            StatisticalAnalysisStageHandler(config, repository, statistical_analysis),
            ResultFreezeStageHandler(config, repository),
            ReportGenerationStageHandler(config, repository),
        ),
    )


def _synthetic_materialized_frame(feature_columns: tuple[str, ...], *, client_offset_scale: float) -> pl.DataFrame:
    rng = np.random.default_rng(hash(client_offset_scale) & 0xFFFF)
    rows: list[dict[str, object]] = []
    row_index = 0
    for split, count, is_attack in (
        ("train", 8, False),
        ("calibration", 8, False),
        ("test", 4, False),
        ("test", 4, True),
    ):
        for _ in range(count):
            values = rng.uniform(0.0, 1.0, size=len(feature_columns)) + client_offset_scale
            if is_attack:
                values = values + 5.0
            row: dict[str, object] = {
                "split": split,
                "is_attack": is_attack,
                "source_path": f"client_{client_offset_scale}.csv",
                "source_row_index": row_index,
            }
            row.update(dict(zip(feature_columns, values.tolist(), strict=True)))
            rows.append(row)
            row_index += 1
    schema_overrides: dict[str, pl.DataType | type[pl.DataType]] = {name: pl.Float64 for name in feature_columns}
    schema_overrides["is_attack"] = pl.Boolean
    schema_overrides["source_row_index"] = pl.Int64
    return pl.DataFrame(rows, schema_overrides=schema_overrides)


def _commit(
    repository: AtomicArtifactRepository,
    config,
    relative_path: str,
    key: ArtifactKey,
    artifact_format: ArtifactFormat,
    payload: bytes,
) -> None:
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=key,
                artifact_format=artifact_format,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=payload),
        )
    )
    assert result.success, result.error_message


def _precommit_synthetic_materialization_for_every_seed(app, repository: AtomicArtifactRepository) -> None:
    graph = app.plan_experiment.execute(_EXPERIMENT_ID)
    dataset = app.config.datasets[
        app.config.populations.get(app.config.experiments.get(_EXPERIMENT_ID).population_ids[0]).dataset_id
    ]
    assert dataset.field_schema.model_features is not None
    feature_columns = dataset.field_schema.model_features.order
    materialization_jobs = [job for job in graph.jobs if job.stage is StageKind.DATASET_MATERIALIZATION]
    run_id = execution_run_id(app.config)
    for job in materialization_jobs:
        frames = [
            _synthetic_materialized_frame(feature_columns, client_offset_scale=float(index)).with_columns(
                pl.lit(client).alias("client_id")
            )
            for index, client in enumerate(_CLIENTS)
        ]
        frame = pl.concat(frames)
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        payload = BytesIO()
        frame.write_parquet(payload)
        _commit(repository, app.config, relative_path, job.output, ArtifactFormat.PARQUET, payload.getvalue())
        for suffix, kind in (
            ("split_manifest", ArtifactKind.SPLIT_MANIFEST),
            ("readiness", ArtifactKind.DATASET_READINESS),
            ("preprocessing", ArtifactKind.PREPROCESSING_EVIDENCE),
        ):
            companion_key = ArtifactKey(artifact_id=ArtifactId(f"{job.output.artifact_id.value}:{suffix}"), kind=kind)
            _commit(
                repository,
                app.config,
                f"{relative_path}.{suffix}",
                companion_key,
                ArtifactFormat.JSON,
                suffix.encode("utf-8"),
            )


def execution_run_id(config):
    from datp_core.domain.run_identity import execution_run_id as _run_id_fn

    return _run_id_fn(_EXPERIMENT_ID, config.execution_fingerprint.value)


def test_full_bounded_synthetic_pipeline_reaches_terminal_success_and_resumes(tmp_path) -> None:
    app = build_application()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    _precommit_synthetic_materialization_for_every_seed(app, repository)
    executor = _build_executor(app.config, repository)

    first_report = executor.execute(_EXPERIMENT_ID)

    assert first_report.failed_jobs == 0
    non_terminal = [
        outcome
        for outcome in first_report.outcomes
        if outcome.status not in (JobExecutionStatus.SUCCESS, JobExecutionStatus.REUSED)
    ]
    assert non_terminal == [], [(o.stage, o.status, o.error_message) for o in non_terminal]
    by_stage = {}
    for outcome in first_report.outcomes:
        by_stage.setdefault(outcome.stage, []).append(outcome.status)
    assert all(status is JobExecutionStatus.REUSED for status in by_stage[StageKind.DATASET_MATERIALIZATION])
    assert all(status is JobExecutionStatus.SUCCESS for status in by_stage[StageKind.MODEL_TRAINING])
    assert all(status is JobExecutionStatus.SUCCESS for status in by_stage[StageKind.SCORE_GENERATION])
    assert all(status is JobExecutionStatus.SUCCESS for status in by_stage[StageKind.THRESHOLD_CONSTRUCTION])
    assert all(status is JobExecutionStatus.SUCCESS for status in by_stage[StageKind.OPERATING_POINT_EVALUATION])
    assert by_stage[StageKind.STATISTICAL_ANALYSIS] == [JobExecutionStatus.SUCCESS]
    assert by_stage[StageKind.RESULT_FREEZE] == [JobExecutionStatus.SUCCESS]
    assert by_stage[StageKind.REPORT_GENERATION] == [JobExecutionStatus.SUCCESS]

    report_job = next(
        job for job in app.plan_experiment.execute(_EXPERIMENT_ID).jobs if job.stage is StageKind.REPORT_GENERATION
    )
    run_id = execution_run_id(app.config)
    report_read = repository.read(f"runs/{run_id.value}/{report_job.job_id.value}")
    assert report_read.found and report_read.payload_bytes is not None
    rendered = json.loads(report_read.payload_bytes)
    assert rendered["experiment_id"] == _EXPERIMENT_ID.value
    labels = {item["profile_id"] for item in rendered["rendered_artifacts"]}
    assert "interval_table" in labels
    table = next(item for item in rendered["rendered_artifacts"] if item["profile_id"] == "interval_table")
    assert "shared_mean_p95 vs local_p95" in table["outputs"]["markdown"]

    statistical_job = next(
        job for job in app.plan_experiment.execute(_EXPERIMENT_ID).jobs if job.stage is StageKind.STATISTICAL_ANALYSIS
    )
    statistical_read = repository.read(f"runs/{run_id.value}/{statistical_job.job_id.value}")
    assert statistical_read.found and statistical_read.payload_bytes is not None
    results = json.loads(statistical_read.payload_bytes)
    labels_seen = {item["analysis_label"] for item in results}
    assert labels_seen == {"anchor_scope_effect", "anchor_equivalence"}
    scope_effect = next(item for item in results if item["analysis_label"] == "anchor_scope_effect")
    assert len(scope_effect["seed_differences"]) == 5
    assert scope_effect["resample_count"] > 0

    second_report = executor.execute(_EXPERIMENT_ID)

    assert second_report.failed_jobs == 0
    assert second_report.successful_jobs == 0
    assert second_report.reused_jobs == len(second_report.outcomes)
    second_statistical_read = repository.read(f"runs/{run_id.value}/{statistical_job.job_id.value}")
    assert second_statistical_read.payload_bytes == statistical_read.payload_bytes
