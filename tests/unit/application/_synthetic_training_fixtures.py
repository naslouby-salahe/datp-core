"""Shared synthetic-data builders for stage-handler tests that need real materialized
Parquet, checkpoint, or score content rather than opaque placeholder bytes.

These helpers exist because ModelTrainingStageHandler, ScoreGenerationStageHandler, and
CalibrationSubsamplingStageHandler all read and parse their inputs for real (unlike stages
whose reuse path only checks artifact metadata), so a test exercising their production code
path needs schema-correct synthetic content, not just a byte blob.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
import polars as pl
from safetensors.torch import save as save_safetensors

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactId,
    ArtifactKey,
    ArtifactKind,
    BytesPayload,
)
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository
from datp_core.infrastructure.learning.pytorch_adapter import DynamicDenseAutoencoder, set_deterministic_seeds


def build_synthetic_materialized_frame(
    feature_columns: tuple[str, ...],
    *,
    clients: tuple[str, ...] = ("client_a", "client_b"),
    train_rows_per_client: int = 6,
    calibration_rows_per_client: int = 6,
    test_benign_rows_per_client: int = 3,
    test_attack_rows_per_client: int = 3,
    random_seed: int = 0,
) -> pl.DataFrame:
    """Build a schema-correct synthetic materialized dataset with real finite feature values."""
    rng = np.random.default_rng(random_seed)
    rows: list[dict[str, object]] = []
    row_index = 0
    for client in clients:
        for split, count, is_attack in (
            ("train", train_rows_per_client, False),
            ("calibration", calibration_rows_per_client, False),
            ("test", test_benign_rows_per_client, False),
            ("test", test_attack_rows_per_client, True),
        ):
            for _ in range(count):
                row: dict[str, object] = {
                    "split": split,
                    "client_id": client,
                    "is_attack": is_attack,
                    "source_path": f"{client}.csv",
                    "source_row_index": row_index,
                }
                values = rng.uniform(0.0, 1.0, size=len(feature_columns))
                if is_attack:
                    values = values + 5.0
                row.update(dict(zip(feature_columns, values.tolist(), strict=True)))
                rows.append(row)
                row_index += 1
    schema_overrides: dict[str, pl.DataType | type[pl.DataType]] = {name: pl.Float64 for name in feature_columns}
    schema_overrides["is_attack"] = pl.Boolean
    schema_overrides["source_row_index"] = pl.Int64
    return pl.DataFrame(rows, schema_overrides=schema_overrides)


def commit_materialized_dataset(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    *,
    run_id_value: str,
    job_id_value: str,
    output_key: ArtifactKey,
    frame: pl.DataFrame,
) -> None:
    """Commit a real materialized dataset plus its three required companion artifacts.

    Companion split-manifest/readiness/preprocessing content is not read by training or
    scoring, only checked for presence by the reuse-assessment path, so placeholder bytes
    are sufficient there -- matching the established pattern in
    test_dataset_materialization_reuse.py.
    """
    relative_path = f"runs/{run_id_value}/{job_id_value}"
    payload = BytesIO()
    frame.write_parquet(payload)
    _commit(repository, config, relative_path, output_key, BytesPayload(payload_bytes=payload.getvalue()))
    for suffix, kind in (
        ("split_manifest", ArtifactKind.SPLIT_MANIFEST),
        ("readiness", ArtifactKind.DATASET_READINESS),
        ("preprocessing", ArtifactKind.PREPROCESSING_EVIDENCE),
    ):
        companion_key = ArtifactKey(artifact_id=ArtifactId(f"{output_key.artifact_id.value}:{suffix}"), kind=kind)
        _commit(
            repository,
            config,
            f"{relative_path}.{suffix}",
            companion_key,
            BytesPayload(payload_bytes=suffix.encode("utf-8")),
        )


def build_single_round_checkpoint(
    feature_columns: tuple[str, ...], hidden_dims: tuple[int, ...], *, round_number: int, seed: int
) -> tuple[bytes, DynamicDenseAutoencoder]:
    """Build one deterministic, real (non-random-at-test-time) autoencoder checkpoint."""
    set_deterministic_seeds(seed)
    model = DynamicDenseAutoencoder(len(feature_columns), hidden_dims)
    model.eval()
    state = {f"round_{round_number}.{name}": tensor for name, tensor in model.state_dict().items()}
    return save_safetensors(state), model


def _commit(
    repository: AtomicArtifactRepository,
    config: ResolvedProjectConfiguration,
    relative_path: str,
    artifact_key: ArtifactKey,
    payload: BytesPayload,
) -> None:
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=ArtifactFormat.PARQUET
                if artifact_key.kind
                in {ArtifactKind.MATERIALIZED_DATASET, ArtifactKind.CALIBRATION_SCORES, ArtifactKind.TEST_SCORES}
                else ArtifactFormat.JSON,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=payload,
        )
    )
    assert result.success, result.error_message
