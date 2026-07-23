"""Shared helpers for committing synthetic-but-schema-correct upstream artifacts that the
StatisticalAnalysisStageHandler's `_analyze_*` methods read directly from the repository.

These tests exercise the real private analysis methods (or the full `.execute()` dispatch)
against real, unmodified experiment configuration -- never an invented experiment -- so the
only synthetic part is the small numeric content of each committed Parquet/JSON/checkpoint
artifact, always written at the exact relative path an `IdentityBuilder.*_job_id` builder
would resolve for the given `StageJobContext`.
"""

from __future__ import annotations

import json
from io import BytesIO

import polars as pl
import torch
from safetensors.torch import save as save_safetensors

from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    BytesPayload,
)
from datp_core.artifacts.repository import AtomicArtifactRepository


def commit_parquet(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    relative_path: str,
    artifact_key: ArtifactKey,
    frame: pl.DataFrame,
) -> None:
    payload = BytesIO()
    frame.write_parquet(payload)
    _commit(repository, config, relative_path, artifact_key, ArtifactFormat.PARQUET, payload.getvalue())


def commit_json(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    relative_path: str,
    artifact_key: ArtifactKey,
    payload: object,
) -> None:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    _commit(repository, config, relative_path, artifact_key, ArtifactFormat.JSON, encoded)


def commit_checkpoint(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    relative_path: str,
    artifact_key: ArtifactKey,
    tensors: dict[str, torch.Tensor],
) -> None:
    _commit(repository, config, relative_path, artifact_key, ArtifactFormat.SAFETENSORS, save_safetensors(tensors))


def _commit(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    relative_path: str,
    artifact_key: ArtifactKey,
    artifact_format: ArtifactFormat,
    payload_bytes: bytes,
) -> None:
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=artifact_format,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=payload_bytes),
        )
    )
    assert result.success, result.error_message


def client_metric_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    """Build a schema-correct client-metric frame from partial per-client rows.

    Each row only needs to specify the fields relevant to the analysis under test; every
    other required column is defaulted to an "available" benign/attack confusion-count shape
    so callers do not have to repeat schema boilerplate for fields they do not exercise.
    """
    defaults = {
        "true_positives": 0,
        "false_positives": 0,
        "true_negatives": 0,
        "false_negatives": 0,
        "false_positive_rate": None,
        "false_positive_rate_status": "available",
        "true_positive_rate": None,
        "true_positive_rate_status": "unavailable_missing_attack_class",
        "balanced_accuracy": None,
        "balanced_accuracy_status": "unavailable_missing_attack_class",
        "macro_f1": None,
        "macro_f1_status": "unavailable_missing_attack_class",
        "auroc": None,
        "auroc_status": "unavailable_single_class",
    }
    full_rows = [{**defaults, **row} for row in rows]
    float_columns = (
        "false_positive_rate",
        "true_positive_rate",
        "balanced_accuracy",
        "macro_f1",
        "auroc",
    )
    int_columns = ("true_positives", "false_positives", "true_negatives", "false_negatives")
    schema_overrides: dict[str, pl.DataType | type[pl.DataType]] = {name: pl.Float64 for name in float_columns}
    schema_overrides.update({name: pl.Int64 for name in int_columns})
    return pl.DataFrame(full_rows, schema_overrides=schema_overrides)
