from pathlib import Path

import polars as pl

from datp_core.core.identifiers import AvailabilityStatus, CanonicalizationContractName, DatasetId
from datp_core.core.numeric import LogicalElementCount, RowCount, ValidationIssueCount
from datp_core.data.contracts import (
    CanonicalAssetRole,
    DatasetValidationReport,
    ExclusionReason,
    MaterializedDataset,
    SourceFileRole,
)
from datp_core.data.materialization import (
    CanonicalAsset,
    CanonicalPublication,
    MaterializationProgress,
    canonical_data_partition_assets,
    canonical_directory,
    excluded_source_file,
    publish_canonical,
    raw_inventory,
    raw_source_file,
    stream_parquet,
)

from .reader import NBaIoTReader
from .schema import (
    NBAIOT_ARROW_SCHEMA,
    NBAIOT_SCHEMA,
    NBaIoTArtifactName,
    NBaIoTSourceLabel,
    parse_source_identity,
    source_relative_path,
)

_NBAIOT_CANONICALIZATION_CONTRACT = CanonicalizationContractName("normalized_physical_client_identity")


class NBaIoTMaterializer:
    def canonical_directory(self, canonical_root: Path) -> Path:
        return canonical_directory(canonical_root, NBAIOT_SCHEMA)

    def publish(
        self,
        raw_root: Path,
        canonical_root: Path,
        *,
        progress: MaterializationProgress | None = None,
    ) -> MaterializedDataset[CanonicalAssetRole, CanonicalAssetRole]:
        candidates = tuple(sorted(raw_root.glob(f"**/*{NBaIoTArtifactName.CSV_SUFFIX}")))
        demonstration_file = NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
        sources = tuple(path for path in candidates if path.name != demonstration_file)
        excluded_paths = tuple(path for path in candidates if path.name == demonstration_file)
        return self.materialize(sources, canonical_root, excluded_paths=excluded_paths, progress=progress)

    def materialize(
        self,
        source_paths: tuple[Path, ...],
        canonical_root: Path,
        *,
        excluded_paths: tuple[Path, ...] = (),
        progress: MaterializationProgress | None = None,
    ) -> MaterializedDataset[CanonicalAssetRole, CanonicalAssetRole]:
        ordered_paths = tuple(sorted(source_paths))
        return publish_canonical(
            self._prepare_publication(
                ordered_paths,
                canonical_root,
                excluded_paths=excluded_paths,
                progress=progress,
            )
        )

    @staticmethod
    def _prepare_publication(
        source_paths: tuple[Path, ...],
        canonical_root: Path,
        *,
        excluded_paths: tuple[Path, ...] = (),
        progress: MaterializationProgress | None = None,
    ) -> CanonicalPublication[CanonicalAssetRole, CanonicalAssetRole]:
        reader = NBaIoTReader()
        total = len(source_paths)
        frames: list[pl.LazyFrame] = []
        for index, path in enumerate(source_paths):
            if progress is not None:
                progress(f"nbaiot reading source {index + 1}/{total} {path.name}")
            frames.append(reader.read(path))
        row_counts = tuple(reader.validate_finite_values(frame) for frame in frames)
        inventory = raw_inventory(
            DatasetId.NBAIOT,
            tuple(
                raw_source_file(
                    DatasetId.NBAIOT,
                    path,
                    SourceFileRole.BENIGN
                    if parse_source_identity(path).source_label is NBaIoTSourceLabel.BENIGN
                    else SourceFileRole.ATTACK,
                    RowCount(row_count.value),
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
            RowCount(sum(count.value for count in row_counts)),
            RowCount(0),
            RowCount(0),
            ValidationIssueCount(0),
            AvailabilityStatus.AVAILABLE,
        )
        expected_assets = canonical_data_partition_assets(LogicalElementCount(len(frames)))

        def write_assets(data_root: Path) -> tuple[CanonicalAsset[CanonicalAssetRole], ...]:
            written: list[CanonicalAsset[CanonicalAssetRole]] = []
            for index, (frame, asset) in enumerate(zip(frames, expected_assets, strict=True)):
                if progress is not None:
                    progress(f"nbaiot writing canonical asset {index + 1}/{len(expected_assets)} {asset.relative_path}")
                written.append(stream_parquet(frame, data_root, asset, NBAIOT_ARROW_SCHEMA))
            return tuple(written)

        return CanonicalPublication(
            canonical_root=canonical_root,
            canonicalization_contract=_NBAIOT_CANONICALIZATION_CONTRACT,
            schema=NBAIOT_SCHEMA,
            inventory=inventory,
            validation_report=report,
            expected_assets=expected_assets,
            writer=write_assets,
        )
