"""Canonical materialization for audited N-BaIoT sources."""

from pathlib import Path

from datp_core.datasets.canonical_cache import CanonicalAsset, canonical_directory
from datp_core.datasets.contracts import (
    CanonicalAssetRole,
    DatasetValidationReport,
    ExclusionReason,
    MaterializedDataset,
    SourceFileRole,
)
from datp_core.datasets.materialization import (
    CanonicalPublication,
    canonical_data_partition_assets,
    excluded_source_file,
    raw_inventory,
    raw_source_file,
    stream_parquet,
)
from datp_core.datasets.materialization_lifecycle import CanonicalMaterializationRequest, materialize_canonical
from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values.counts import RowCount, ValidationIssueCount

from .reader import NBaIoTReader
from .schema import (
    NBAIOT_ARROW_SCHEMA,
    NBAIOT_SCHEMA,
    NBaIoTArtifactName,
    NBaIoTSourceLabel,
    parse_source_identity,
    source_relative_path,
)

_NBAIOT_CANONICALIZATION_CONTRACT = "normalized_physical_client_identity"


class NBaIoTMaterializer:
    """Publish independently streamed source partitions with complete provenance."""

    def canonical_directory(self, canonical_root: Path) -> Path:
        return canonical_directory(canonical_root, NBAIOT_SCHEMA)

    def publish(self, raw_root: Path, canonical_root: Path) -> MaterializedDataset:
        candidates = tuple(sorted(raw_root.glob(f"**/*{NBaIoTArtifactName.CSV_SUFFIX}")))
        demonstration_file = NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
        sources = tuple(path for path in candidates if path.name != demonstration_file)
        excluded_paths = tuple(path for path in candidates if path.name == demonstration_file)
        return self.materialize(sources, canonical_root, excluded_paths=excluded_paths)

    def materialize(
        self,
        source_paths: tuple[Path, ...],
        canonical_root: Path,
        *,
        excluded_paths: tuple[Path, ...] = (),
    ) -> MaterializedDataset:
        ordered_paths = tuple(sorted(source_paths))
        return materialize_canonical(
            CanonicalMaterializationRequest(
                canonical_root=canonical_root,
                schema=NBAIOT_SCHEMA,
                canonicalization_contract=_NBAIOT_CANONICALIZATION_CONTRACT,
                source_paths=ordered_paths,
                source_path_resolver=source_relative_path,
                asset_role_type=CanonicalAssetRole,
                prepare_publication=lambda: self._prepare_publication(
                    ordered_paths,
                    canonical_root,
                    excluded_paths=excluded_paths,
                ),
            )
        )

    @staticmethod
    def _prepare_publication(
        source_paths: tuple[Path, ...],
        canonical_root: Path,
        *,
        excluded_paths: tuple[Path, ...] = (),
    ) -> CanonicalPublication:
        reader = NBaIoTReader()
        frames = tuple(reader.read(path) for path in source_paths)
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
                    RowCount(row_count),
                    source_relative_path,
                )
                for path, row_count in zip(source_paths, row_counts, strict=True)
            ),
            excluded_sources=tuple(
                excluded_source_file(
                    DatasetId.NBAIOT,
                    path,
                    ExclusionReason.UNRECOGNIZED_SOURCE,
                    source_relative_path,
                )
                for path in excluded_paths
            ),
        )
        report = DatasetValidationReport(
            DatasetId.NBAIOT,
            (),
            (),
            RowCount(sum(row_counts)),
            RowCount(0),
            RowCount(0),
            ValidationIssueCount(0),
            AvailabilityStatus.AVAILABLE,
        )
        expected_assets = canonical_data_partition_assets(len(frames))

        def write_assets(data_root: Path) -> tuple[CanonicalAsset, ...]:
            return tuple(
                stream_parquet(frame, data_root, asset, NBAIOT_ARROW_SCHEMA)
                for frame, asset in zip(frames, expected_assets, strict=True)
            )

        return CanonicalPublication(
            canonical_root=canonical_root,
            canonicalization_contract=_NBAIOT_CANONICALIZATION_CONTRACT,
            schema=NBAIOT_SCHEMA,
            inventory=inventory,
            validation_report=report,
            expected_assets=expected_assets,
            writer=write_assets,
            source_paths=source_paths,
            source_path_resolver=source_relative_path,
        )
