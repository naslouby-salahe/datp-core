"""Integration test: stage handler artifact read/evaluate/write cycle."""

from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path

import polars as pl

from datp_core.artifacts.store import ArtifactStore, Checksum
from datp_core.core.identifiers import ExperimentId, ThresholdPolicyId
from datp_core.evaluation.enums import MissingThresholdPolicy
from datp_core.evaluation.stage import OperatingPointEvaluationStageHandler
from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.stages.context import EvaluationContext
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.jobs import StageInput, StageJob, StageOutput


def _make_threshold_parquet() -> bytes:
    df = pl.DataFrame(
        {
            "client_id": ["a", "b"],
            "threshold": [0.5, 0.3],
            "policy_kind": ["local"] * 2,
            "scope": ["per_client"] * 2,
            "effective_lambda": [None, None],
            "cluster_label": [None, None],
            "finite_sample_rank": [None, None],
            "policy_id": ["shared_mean_p95"] * 2,
            "target_quantile": [0.95, 0.95],
        },
        schema={
            "client_id": pl.String,
            "threshold": pl.Float64,
            "policy_kind": pl.String,
            "scope": pl.String,
            "effective_lambda": pl.Float64,
            "cluster_label": pl.Int64,
            "finite_sample_rank": pl.Int64,
            "policy_id": pl.String,
            "target_quantile": pl.Float64,
        },
    )
    buf = BytesIO()
    df.write_parquet(buf)
    return buf.getvalue()


def _make_score_parquet() -> bytes:
    df = pl.DataFrame(
        {
            "client_id": ["a", "a", "b", "b"],
            "score": [0.1, 0.9, 0.2, 0.8],
            "label": [0, 1, 0, 1],
        },
        schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
    )
    buf = BytesIO()
    df.write_parquet(buf)
    return buf.getvalue()


class _InMemoryStore(ArtifactStore):
    def __init__(self) -> None:
        super().__init__(root=Path(tempfile.mkdtemp()))
        self._data: dict[str, bytes] = {}

    def read_bytes(self, relative_path: str) -> bytes:
        return self._data[relative_path]

    def write_bytes_atomic(self, relative_path: str, payload: bytes, *, replace: bool = False) -> Checksum:
        if not replace and relative_path in self._data:
            raise FileExistsError(f"Artifact already exists: {relative_path}")
        self._data[relative_path] = payload
        return Checksum("0" * 64)

    def exists(self, relative_path: str) -> bool:
        return relative_path in self._data


def _make_job(ctx: EvaluationContext, node_label: str) -> StageJob:
    producer = GraphNodeKey("producer")
    return StageJob(
        node_key=GraphNodeKey(node_label),
        stage=StageKind.OPERATING_POINT_EVALUATION,
        context=ctx,
        dependencies=(producer,),
        inputs=(
            StageInput(name="thresholds", relative_path="thresholds.parquet", producer=producer),
            StageInput(name="test_scores", relative_path="test_scores.parquet", producer=producer),
        ),
        outputs=(
            StageOutput(name="client_metrics", relative_path="client_metrics.parquet"),
        ),
    )


def _make_context(*, threshold_policy_id: ThresholdPolicyId) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=ExperimentId("test"),
        threshold_policy_id=threshold_policy_id,
        missing_threshold_policy=MissingThresholdPolicy.FAIL,
        seed=0,
        calibration_sample_count=None,
        calibration_replicate=None,
    )


def test_successful_read_evaluate_write_cycle() -> None:
    store = _InMemoryStore()
    handler = OperatingPointEvaluationStageHandler(store)

    store.write_bytes_atomic("thresholds.parquet", _make_threshold_parquet())
    store.write_bytes_atomic("test_scores.parquet", _make_score_parquet())

    job = _make_job(_make_context(threshold_policy_id=ThresholdPolicyId("shared_mean_p95")), "eval_node")
    outcome = handler.execute(job)
    assert outcome.status is JobExecutionStatus.SUCCESS

    result = pl.read_parquet(BytesIO(store.read_bytes("client_metrics.parquet")))
    assert result.height == 2
    assert "auroc" in result.columns
    assert "policy_id" in result.columns


def test_malformed_threshold_artifact_fails() -> None:
    store = _InMemoryStore()
    handler = OperatingPointEvaluationStageHandler(store)

    bad_thresholds = pl.DataFrame({"wrong_column": [1]}, schema={"wrong_column": pl.Int64})
    buf = BytesIO()
    bad_thresholds.write_parquet(buf)
    store.write_bytes_atomic("thresholds.parquet", buf.getvalue())
    store.write_bytes_atomic("test_scores.parquet", _make_score_parquet())

    job = _make_job(_make_context(threshold_policy_id=ThresholdPolicyId("shared_mean_p95")), "eval_node")
    outcome = handler.execute(job)
    assert outcome.status is JobExecutionStatus.FAILED
