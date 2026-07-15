from dataclasses import dataclass
from pathlib import Path

import msgspec
import pyarrow.csv as pa_csv

from datp_core.application.ports.data import InspectDatasetSourceRequest
from datp_core.application.ports.persistence import WriteArtifactRequest
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    DatasetArtifactKey,
    SerializationFormat,
    WriteDisposition,
)
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import (
    Dataset,
    DatasetSourceInspectionResult,
    DatasetSourceManifest,
    FeatureSchemaManifest,
    SourceFileManifestEntry,
    SourceTrafficLabel,
)
from datp_core.domain.errors import DatasetError
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash, blake3_file_content_hash

_CSV_STREAM_BLOCK_BYTES = 8 * 1024 * 1024
_TIMESTAMP_KEYWORDS = ("timestamp", "capture_time", "packet_time", "event_time")


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTSourceInspector:
    raw_root: Path
    artifact_store: FileArtifactStore

    def inspect(self, request: InspectDatasetSourceRequest) -> DatasetSourceInspectionResult:
        device_dirs = sorted_device_directories(self.raw_root)
        if not device_dirs:
            raise _dataset_error(request, f"no device directories found beneath {self.raw_root}")
        feature_columns: tuple[str, ...] | None = None
        source_files: list[SourceFileManifestEntry] = []
        for device_dir in device_dirs:
            for csv_path, label in device_csv_files(device_dir):
                columns, row_count = _inspect_csv(csv_path)
                if columns is None:
                    raise _dataset_error(request, f"{csv_path} contains no rows")
                if feature_columns is None:
                    feature_columns = columns
                elif columns != feature_columns:
                    raise _dataset_error(
                        request, f"{csv_path} has a feature schema that differs from the first inspected file"
                    )
                source_files.append(
                    SourceFileManifestEntry(
                        relative_path=csv_path.relative_to(self.raw_root).as_posix(),
                        device_id=device_dir.name,
                        label=label,
                        row_count=row_count,
                        content_hash=blake3_file_content_hash(csv_path),
                    )
                )
        if feature_columns is None:
            raise _dataset_error(request, "no source files were found to inspect")
        if len(feature_columns) != request.dataset.input_dim:
            raise _dataset_error(
                request,
                "inspected feature column count does not match the configured input dimension",
            )
        source_manifest = DatasetSourceManifest(
            dataset=request.dataset.dataset,
            device_ids=tuple(device_dir.name for device_dir in device_dirs),
            source_files=tuple(source_files),
            total_row_count=sum(entry.row_count for entry in source_files),
        )
        feature_schema_manifest = FeatureSchemaManifest(
            dataset=request.dataset.dataset,
            feature_columns=feature_columns,
            input_dim=len(feature_columns),
        )
        source_manifest_ref, source_content_hash = self._persist(
            request.dataset.dataset, source_manifest, ArtifactType.SOURCE_INSPECTION
        )
        feature_schema_manifest_ref, _ = self._persist(
            request.dataset.dataset, feature_schema_manifest, ArtifactType.FEATURE_SCHEMA_MANIFEST
        )
        _reject_unexpected_timestamp_column(feature_columns)
        return DatasetSourceInspectionResult(
            source_manifest=source_manifest_ref,
            feature_schema_manifest=feature_schema_manifest_ref,
            source_row_identity=DatasetSourceIdentity(value=StageFingerprint(value=source_content_hash)),
            timestamp_evidence=None,
        )

    def _persist(
        self, dataset: Dataset, manifest: DatasetSourceManifest | FeatureSchemaManifest, artifact_type: ArtifactType
    ) -> tuple[ArtifactRef, str]:
        content = msgspec.json.encode(manifest)
        content_hash = blake3_bytes_content_hash(content)
        artifact = ArtifactRef(
            artifact_id=ArtifactId(value=f"artifact-{content_hash}"),
            artifact_type=artifact_type,
            content_hash=content_hash,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.JSON,
        )
        key = DatasetArtifactKey(
            artifact_type=artifact_type,
            dataset=dataset,
            stage_identity=StageFingerprint(value=content_hash),
            namespace=ArtifactNamespace.DATP_ANCHOR,
        )
        result = self.artifact_store.write_atomically(
            WriteArtifactRequest(
                key=key, artifact=artifact, content=content, write_disposition=WriteDisposition.CREATE_IF_ABSENT
            )
        )
        return result.artifact, content_hash


def sorted_device_directories(raw_root: Path) -> tuple[Path, ...]:
    return tuple(sorted((entry for entry in raw_root.iterdir() if entry.is_dir()), key=lambda entry: entry.name))


def device_csv_files(device_dir: Path) -> tuple[tuple[Path, SourceTrafficLabel], ...]:
    entries: list[tuple[Path, SourceTrafficLabel]] = []
    benign_path = device_dir / "benign_traffic.csv"
    if benign_path.is_file():
        entries.append((benign_path, SourceTrafficLabel.BENIGN))
    for family_dir_name, label in (
        ("gafgyt_attacks", SourceTrafficLabel.GAFGYT),
        ("mirai_attacks", SourceTrafficLabel.MIRAI),
    ):
        family_dir = device_dir / family_dir_name
        if family_dir.is_dir():
            for csv_path in sorted(family_dir.glob("*.csv"), key=lambda path: path.name):
                entries.append((csv_path, label))
    return tuple(entries)


def _inspect_csv(path: Path) -> tuple[tuple[str, ...] | None, int]:
    reader = pa_csv.open_csv(path, read_options=pa_csv.ReadOptions(block_size=_CSV_STREAM_BLOCK_BYTES))
    columns: tuple[str, ...] | None = None
    row_count = 0
    for batch in reader:
        if columns is None:
            columns = tuple(batch.schema.names)
        row_count += batch.num_rows
    return columns, row_count


def _reject_unexpected_timestamp_column(feature_columns: tuple[str, ...]) -> None:
    for column in feature_columns:
        if any(keyword in column.casefold() for keyword in _TIMESTAMP_KEYWORDS):
            raise DatasetError(
                dataset="n_baiot",
                regime="unresolved",
                coverage=f"unexpected timestamp-like column {column!r} requires typed evidence, not a silent guess",
                detail=f"unexpected timestamp-like column {column!r} requires typed evidence, not a silent guess",
            )


def _dataset_error(request: InspectDatasetSourceRequest, coverage: str) -> DatasetError:
    return DatasetError(dataset=request.dataset.dataset.value, regime="unresolved", coverage=coverage, detail=coverage)
