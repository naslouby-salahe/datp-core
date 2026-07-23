from pathlib import Path

import polars as pl

from datp_core.bootstrap import build_application
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    FilePayload,
)
from datp_core.configuration.fingerprints import compute_execution_fingerprint, compute_scientific_fingerprint
from datp_core.pipeline.identifiers import ArtifactId, DatasetId, MaterializationId
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.datasets.nbaiot import consolidate_nbaiot_parquet_sources, write_nbaiot_source_parquet


def test_staged_nbaiot_parquet_consolidation_commits_as_a_frozen_artifact(tmp_path: Path) -> None:
    source_root = tmp_path / "N-BaIoT"
    source = source_root / "device" / "benign_traffic.csv"
    source.parent.mkdir(parents=True)
    source.write_text("feature_1\n" + "\n".join(str(value) for value in range(100)) + "\n")
    materialization = next(
        item
        for item in build_application().config.datasets[DatasetId("nbaiot")].materializations
        if item.identifier == MaterializationId("anchor")
    )
    staged = tmp_path / "staged.parquet"
    write_nbaiot_source_parquet(
        source,
        staged,
        source_root,
        ("feature_1",),
        "benign_traffic.csv",
        ("gafgyt_attacks", "mirai_attacks"),
        materialization,
        7,
    )
    consolidated = tmp_path / "consolidated.parquet"
    assert consolidate_nbaiot_parquet_sources((staged,), consolidated, 7) == 98
    scientific = compute_scientific_fingerprint({"dataset": "nbaiot"})
    repository = AtomicArtifactRepository(tmp_path / "artifacts", lock_timeout=1.0)
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=ArtifactKey(artifact_id=ArtifactId("dataset"), kind=ArtifactKind.MATERIALIZED_DATASET),
            artifact_format=ArtifactFormat.PARQUET,
            scientific_fingerprint=scientific,
            execution_fingerprint=compute_execution_fingerprint({"scientific": scientific}),
            relative_path="datasets/nbaiot",
            parents=(),
            schema_version=1,
            creation_timestamp=1.0,
            environment_identity="test",
        ),
        payload=FilePayload(source_file=str(consolidated)),
    )
    assert repository.commit(request).success
    payload = repository.read("datasets/nbaiot").payload_bytes
    assert payload is not None
    assert pl.read_parquet(payload).height == 98
