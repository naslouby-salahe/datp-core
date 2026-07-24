"""Dataset materialization's resumable partial-family recovery and TOCTOU source-change guard,
against the real `anchor_reproduction` experiment configuration with a fake adapter standing in
for the real (multi-GB) N-BaIoT CSV reader.

A fake `DatasetMaterializer` is used rather than the real adapter: the real datasets in this repo
are 9-17GB, so exercising the real CSV-reading path here would be impractical for a fast test
suite. The fake returns a small, deterministic, schema-correct synthetic split -- exactly what the
real adapter would hand back, just without reading gigabytes of CSV. Everything downstream
(readiness audit, eligibility, reuse assessment, atomic commit, the resumable-recovery logic under
test) is the real, unmodified production code path.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl
import pytest

from datp_core.app import DatpApplication, build_application
from datp_core.artifacts.codecs.manifest import CURRENT_ARTIFACT_SCHEMA_VERSION
from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey
from datp_core.artifacts.payloads import ArtifactCommitMetadata, ArtifactCommitRequest, BytesPayload
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import DatasetId, ExperimentId
from datp_core.pipeline.stages.node_key import StageNodeKey, node_path
from datp_core.data.contracts.dataset import DatasetSetup, ResolvedDataset
from datp_core.data.contracts.enums import AdapterKind
from datp_core.data.contracts.materialization import DatasetMaterialization, PartitionSeedContract
from datp_core.data.materialization import handler as materialization_handler_module
from datp_core.data.materialization.handler import DatasetMaterializationStageHandler
from datp_core.data.materialization.models import MaterializationResult
from datp_core.data.materialization.ports import SourceInventory
from datp_core.data.materialization.registry import DatasetAdapterRegistry
from datp_core.experiments import SweepConditionRecord
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.jobs import StageJob

_EXPECTED_CLIENT_COUNT = 9
_MINIMUM_BENIGN_CALIBRATION_COUNT = 100


def _build_synthetic_nbaiot_split() -> pl.DataFrame:
    """Nine clients (matching `nbaiot.yaml`'s `anchor_natural_devices` `client_count: 9`), each
    with >= 100 benign calibration rows (matching `primary_analysis`'s
    `minimum_benign_calibration_count: 100`), a handful of train rows, and benign+attack test rows
    so `per_client_attack_detection_metrics` is evaluable."""
    rows: list[dict[str, object]] = []
    row_index = 1
    for client_index in range(_EXPECTED_CLIENT_COUNT):
        client_id = f"device_{client_index}"
        for split, count, is_attack in (
            ("train", 5, False),
            ("calibration", _MINIMUM_BENIGN_CALIBRATION_COUNT, False),
            ("test", 3, False),
            ("test", 2, True),
        ):
            for _ in range(count):
                rows.append(
                    {
                        "split": split,
                        "client_id": client_id,
                        "is_attack": is_attack,
                        "source_path": f"{client_id}.csv",
                        "source_row_index": row_index,
                    }
                )
                row_index += 1
    return pl.DataFrame(rows, schema_overrides={"is_attack": pl.Boolean, "source_row_index": pl.Int64})


class _FakeNBaIoTAdapter:
    """Stands in for the real N-BaIoT CSV adapter: always returns the identical deterministic
    synthetic split, regardless of the real (multi-GB) source files on disk."""

    def __init__(self, adapter_kind: AdapterKind) -> None:
        self.adapter_kind = adapter_kind

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
        *,
        chunk_row_count: int,
    ) -> MaterializationResult:
        del dataset, setup, materialization, inventory, partition_condition, partition_seed_contract, chunk_row_count
        frame = _build_synthetic_nbaiot_split()
        staged_path = staging_root / "materialized.parquet"
        frame.write_parquet(staged_path)
        return MaterializationResult(
            staged_path=staged_path, row_count=frame.height, preprocessing_evidence=b"{}", partition_evidence=None
        )


def _materialization_job(app: DatpApplication, seed: int = 0) -> StageJob:
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    return next(
        planned
        for planned in graph.jobs
        if planned.stage is StageKind.DATASET_MATERIALIZATION and planned.context.seed == seed
    )


def _fake_registry(app: DatpApplication) -> DatasetAdapterRegistry:
    job = _materialization_job(app)
    assert job.context.population_id is not None
    population = app.config.populations.get(job.context.population_id)
    dataset = app.config.datasets[DatasetId(population.dataset_id.value)]
    return DatasetAdapterRegistry({dataset.adapter_kind: _FakeNBaIoTAdapter(dataset.adapter_kind)})


def _commit_preflight(
    repository: AtomicArtifactRepository,
    app: DatpApplication,
    preflight_key: ArtifactKey,
    preflight_node_key: StageNodeKey,
) -> None:
    """Commit a preflight artifact so parent-lineage verification passes."""
    relative_path = node_path(preflight_node_key)
    result = repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=preflight_key,
                artifact_format=ArtifactFormat.JSON,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=b"{}"),
        )
    )
    assert result.success, result.error_message


def test_materialization_detects_a_source_change_during_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Closing the TOCTOU window: if the source files change between the pre-materialization
    inventory (used for the reuse check and the run's identity) and the post-materialization
    re-check, the handler must fail explicitly rather than commit under a now-stale fingerprint."""
    app = build_application()
    job = _materialization_job(app)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=30.0)
    _commit_preflight(repository, app, job.inputs[0], job.dependencies[0])
    handler = DatasetMaterializationStageHandler(app.config, repository, _fake_registry(app))

    real_build_source_inventory = materialization_handler_module.build_source_inventory
    call_count = {"n": 0}

    class _DriftingInventory:
        def __init__(self, real_inventory: object, call_index: int) -> None:
            self._real_inventory = real_inventory
            self._call_index = call_index

        def fingerprint(self) -> Checksum:
            if self._call_index == 0:
                return self._real_inventory.fingerprint()  # type: ignore[attr-defined]
            return Checksum(value="f" * 64)

        def __getattr__(self, name: str) -> object:
            return getattr(self._real_inventory, name)

    def _fake_build_source_inventory(dataset: ResolvedDataset) -> object:
        index = call_count["n"]
        call_count["n"] += 1
        return _DriftingInventory(real_build_source_inventory(dataset), index)

    monkeypatch.setattr(materialization_handler_module, "build_source_inventory", _fake_build_source_inventory)

    outcome = handler.execute(job)

    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message is not None
    assert "Source files changed during materialization" in outcome.error_message
    # Nothing must have been committed under the stale identity.
    assert not repository.read(node_path(job.node_key)).found
