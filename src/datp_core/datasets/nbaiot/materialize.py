"""Canonical materialization for audited N-BaIoT sources."""

from pathlib import Path

from datp_core.datasets.canonical_cache import (
    CanonicalAsset,
    CanonicalReuseRequest,
    canonical_directory,
    reuse_published_canonical,
)
from datp_core.datasets.materialization import (
    CanonicalPublication,
    canonical_data_partition_assets,
    publish_canonical,
    raw_inventory,
    raw_source_file,
    stream_parquet,
)
from datp_core.datasets.models import CanonicalAssetRole, DatasetValidationReport, MaterializedDataset, SourceFileRole
from datp_core.domain.enums import AvailabilityStatus, DatasetId

from .reader import NBaIoTReader
from .schema import NBAIOT_ARROW_SCHEMA, NBAIOT_SCHEMA, NBaIoTSourceLabel, parse_source_identity, source_relative_path

_NBAIOT_CANONICALIZATION_CONTRACT = "normalized_physical_client_identity"


class NBaIoTMaterializer:
    """Publish independently streamed source partitions with complete provenance."""

    def canonical_directory(self, canonical_root: Path) -> Path:
        return canonical_directory(canonical_root, NBAIOT_SCHEMA)

    def materialize(self, source_paths: tuple[Path, ...], canonical_root: Path) -> MaterializedDataset:
        if not source_paths:
            raise ValueError("N-BaIoT materialization requires accepted sources")
        ordered_paths = tuple(sorted(source_paths))
        reusable = reuse_published_canonical(
            CanonicalReuseRequest(
                canonical_root=canonical_root,
                schema=NBAIOT_SCHEMA,
                canonicalization_contract=_NBAIOT_CANONICALIZATION_CONTRACT,
                source_paths=ordered_paths,
                source_path_resolver=source_relative_path,
                asset_role_type=CanonicalAssetRole,
            )
        )
        if reusable is not None:
            return reusable
        reader = NBaIoTReader()
        frames = tuple(reader.read(path) for path in ordered_paths)
        row_counts = tuple(reader.validate_finite_values(frame) for frame in frames)
        inventory = raw_inventory(
            DatasetId.NBAIOT,
            tuple(
                raw_source_file(
                    DatasetId.NBAIOT,
                    path,
                    SourceFileRole.BENIGN
                    if parse_source_identity(path)[1] == NBaIoTSourceLabel.BENIGN
                    else SourceFileRole.ATTACK,
                    row_count,
                    source_relative_path,
                )
                for path, row_count in zip(ordered_paths, row_counts, strict=True)
            ),
        )
        report = DatasetValidationReport(
            DatasetId.NBAIOT,
            (),
            (),
            sum(row_counts),
            0,
            0,
            0,
            AvailabilityStatus.AVAILABLE,
        )
        expected_assets = canonical_data_partition_assets(len(frames))

        def write_assets(data_root: Path) -> tuple[CanonicalAsset, ...]:
            return tuple(
                stream_parquet(frame, data_root, asset, NBAIOT_ARROW_SCHEMA)
                for frame, asset in zip(frames, expected_assets, strict=True)
            )

        return publish_canonical(
            CanonicalPublication(
                canonical_root=canonical_root,
                canonicalization_contract=_NBAIOT_CANONICALIZATION_CONTRACT,
                schema=NBAIOT_SCHEMA,
                inventory=inventory,
                validation_report=report,
                expected_assets=expected_assets,
                writer=write_assets,
                source_paths=ordered_paths,
                source_path_resolver=source_relative_path,
            )
        )
