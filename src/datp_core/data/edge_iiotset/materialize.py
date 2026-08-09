"""Canonical materialization for audited Edge-IIoTset sources."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.core.identifiers import AvailabilityStatus, DatasetId
from datp_core.core.numeric import RowCount, ValidationIssueCount
from datp_core.data.canonical_cache import CanonicalAsset, CanonicalAssetLayout, canonical_directory
from datp_core.data.contracts import (
    CanonicalProvenanceColumn,
    ChronologyValidation,
    DatasetValidationCode,
    DatasetValidationIssue,
    DatasetValidationReport,
    MaterializedDataset,
    RawDatasetInventory,
    SourceFileRole,
    ValidationSeverity,
)
from datp_core.data.materialization import (
    CanonicalPublication,
    empty_asset,
    named_assets,
    raw_inventory,
    raw_source_file,
    stream_parquet,
)
from datp_core.data.materialization_lifecycle import CanonicalMaterializationRequest, materialize_canonical

from .chronology import PcapChronology, paired_capture_path, validate_chronology, write_capture_timeline
from .reader import EdgeIIoTsetReader
from .schema import (
    EDGE_ARROW_SCHEMA,
    EDGE_SCHEMA,
    EdgeArtifactName,
    EdgeArtifactSuffix,
    EdgeAssetRole,
    EdgeCanonicalColumn,
    benign_sensor_group,
    source_relative_path,
)


@dataclass(frozen=True, slots=True, eq=False)
class _EdgePublicationInputs:
    benign_paths: tuple[Path, ...]
    benign_frames: tuple[pl.LazyFrame, ...]
    attack_frames: tuple[pl.LazyFrame, ...]
    chronology: tuple[PcapChronology, ...]
    expected_assets: tuple[CanonicalAssetLayout[EdgeAssetRole], ...]


@dataclass(frozen=True, slots=True)
class _EdgePublication:
    inputs: _EdgePublicationInputs
    inventory: RawDatasetInventory
    report: DatasetValidationReport
    validations: tuple[ChronologyValidation, ...]


_STATIC_BENIGN_BRANCH = Path(EdgeAssetRole.STATIC_BENIGN.value)
_TEMPORAL_BENIGN_BRANCH = Path(EdgeAssetRole.TEMPORAL_BENIGN.value)
_UNASSIGNED_ATTACK_BRANCH = Path(EdgeAssetRole.UNASSIGNED_ATTACK.value)
_EDGE_CANONICALIZATION_CONTRACT = "pcap_verified_source_order_and_typed_asset_roles"


def _source_paths(benign_paths: tuple[Path, ...], attack_paths: tuple[Path, ...]) -> tuple[Path, ...]:
    evidence_paths = tuple(path for path in (paired_capture_path(path) for path in benign_paths) if path.is_file())
    return tuple(sorted(benign_paths + evidence_paths + attack_paths))


class EdgeIIoTsetMaterializer:
    """Publish static benign, chronology-eligible benign, and unassigned attack partitions."""

    def canonical_directory(self, canonical_root: Path) -> Path:
        return canonical_directory(canonical_root, EDGE_SCHEMA)

    def publish(self, raw_root: Path, canonical_root: Path) -> MaterializedDataset[EdgeAssetRole, EdgeAssetRole]:
        bundle_root = raw_root / EdgeArtifactName.DATASET_BUNDLE_DIRECTORY
        benign_paths = tuple(
            sorted((bundle_root / EdgeArtifactName.NORMAL_TRAFFIC_DIRECTORY).glob(f"*/*{EdgeArtifactSuffix.CSV}"))
        )
        attack_paths = tuple(
            sorted(
                (bundle_root / EdgeArtifactName.ATTACK_TRAFFIC_DIRECTORY).glob(
                    f"*{EdgeArtifactName.ATTACK_FILE_SUFFIX}"
                )
            )
        )
        return self.materialize(benign_paths, attack_paths, canonical_root)

    def materialize(
        self,
        benign_paths: tuple[Path, ...],
        attack_paths: tuple[Path, ...],
        canonical_root: Path,
    ) -> MaterializedDataset[EdgeAssetRole, EdgeAssetRole]:
        ordered_benign = tuple(sorted(benign_paths))
        ordered_attack = tuple(sorted(attack_paths))
        if not ordered_benign or not ordered_attack:
            raise ValueError("Edge materialization requires benign and attack sources")
        source_paths = _source_paths(ordered_benign, ordered_attack)
        return materialize_canonical(
            CanonicalMaterializationRequest(
                canonical_root=canonical_root,
                schema=EDGE_SCHEMA,
                canonicalization_contract=_EDGE_CANONICALIZATION_CONTRACT,
                source_paths=source_paths,
                source_path_resolver=source_relative_path,
                asset_role_type=EdgeAssetRole,
                prepare_publication=lambda: self._prepare_canonical_publication(
                    ordered_benign,
                    ordered_attack,
                    canonical_root,
                    source_paths,
                ),
            )
        )

    def _prepare_canonical_publication(
        self,
        benign_paths: tuple[Path, ...],
        attack_paths: tuple[Path, ...],
        canonical_root: Path,
        source_paths: tuple[Path, ...],
    ) -> CanonicalPublication[EdgeAssetRole, EdgeAssetRole]:
        publication = self._prepare_publication(benign_paths, attack_paths)

        def write_assets(output_root: Path) -> tuple[CanonicalAsset[EdgeAssetRole], ...]:
            return self._write_assets(output_root, publication.inputs)

        return CanonicalPublication(
            canonical_root=canonical_root,
            canonicalization_contract=_EDGE_CANONICALIZATION_CONTRACT,
            schema=EDGE_SCHEMA,
            inventory=publication.inventory,
            validation_report=publication.report,
            expected_assets=publication.inputs.expected_assets,
            writer=write_assets,
            source_paths=source_paths,
            source_path_resolver=source_relative_path,
            chronology=publication.validations,
        )

    def _prepare_publication(self, benign_paths: tuple[Path, ...], attack_paths: tuple[Path, ...]) -> _EdgePublication:
        reader = EdgeIIoTsetReader()
        benign_frames = tuple(reader.read_benign(path) for path in benign_paths)
        attack_frames = tuple(reader.read_attack(path) for path in attack_paths)
        chronology = tuple(
            validate_chronology(
                benign_sensor_group(path).value,
                path,
                paired_capture_path(path),
            )
            for path in benign_paths
        )
        validations = tuple(evidence.validation for evidence in chronology)
        attack_counts = tuple(self._row_count(frame) for frame in attack_frames)
        inventory = self._inventory(benign_paths, chronology, attack_paths, attack_counts)
        report = self._validation_report(benign_paths, validations, attack_counts)
        expected_assets = _expected_assets(benign_paths, attack_paths, validations)
        inputs = _EdgePublicationInputs(benign_paths, benign_frames, attack_frames, chronology, expected_assets)
        return _EdgePublication(inputs, inventory, report, validations)

    @staticmethod
    def _inventory(
        benign_paths: tuple[Path, ...],
        chronology: tuple[PcapChronology, ...],
        attack_paths: tuple[Path, ...],
        attack_counts: tuple[int, ...],  # TODO: should be RowCount instead of int and adapt all callers and usage
    ) -> RawDatasetInventory:
        benign_sources = tuple(
            raw_source_file(
                DatasetId.EDGE_IIOTSET,
                path,
                SourceFileRole.BENIGN,
                evidence.validation.total_rows,
                source_relative_path,
            )
            for path, evidence in zip(benign_paths, chronology, strict=True)
        )
        evidence_sources = tuple(
            raw_source_file(
                DatasetId.EDGE_IIOTSET,
                evidence.pcap_path,
                SourceFileRole.CHRONOLOGY_EVIDENCE,
                None,
                source_relative_path,
            )
            for evidence in chronology
            if evidence.pcap_path.is_file()
        )
        attack_sources = tuple(
            raw_source_file(
                DatasetId.EDGE_IIOTSET,
                path,
                SourceFileRole.ATTACK,
                RowCount(row_count),
                source_relative_path,
            )
            for path, row_count in zip(attack_paths, attack_counts, strict=True)
        )
        return raw_inventory(DatasetId.EDGE_IIOTSET, benign_sources + evidence_sources + attack_sources)

    @staticmethod
    def _write_assets(
        canonical_root: Path,
        inputs: _EdgePublicationInputs,
    ) -> tuple[CanonicalAsset[EdgeAssetRole], ...]:
        timeline_root = canonical_root / ".chronology"
        try:
            static_assets = _write_static_assets(canonical_root, timeline_root, inputs)
            temporal_assets = _write_temporal_assets(canonical_root, static_assets, inputs)
            attack_assets = _write_attack_assets(canonical_root, static_assets, temporal_assets, inputs)
            return static_assets + temporal_assets + attack_assets
        finally:
            rmtree(timeline_root, ignore_errors=True)

    @staticmethod
    def _row_count(
        frame: pl.LazyFrame,
    ) -> int:  # TODO: should be RowCount instead of int and adapt all callers and usage
        return int(frame.select(pl.len()).collect(engine="streaming").item())

    @staticmethod
    def _validation_report(
        benign_paths: tuple[Path, ...],
        validations: tuple[ChronologyValidation, ...],
        attack_counts: tuple[int, ...],  # TODO: should be RowCount instead of int and adapt all callers and usage
    ) -> DatasetValidationReport:
        invalid = tuple(
            (path, validation)
            for path, validation in zip(benign_paths, validations, strict=True)
            if not validation.temporal_eligible
        )
        issues = tuple(
            DatasetValidationIssue(
                ValidationSeverity.WARNING,
                DatasetValidationCode.TEMPORAL_CHRONOLOGY_UNAVAILABLE,
                DatasetId.EDGE_IIOTSET,
                source_relative_path(path).as_posix(),
                validation.reason,
                RowCount(validation.total_rows.value),
            )
            for path, validation in invalid
        )
        return DatasetValidationReport(
            DatasetId.EDGE_IIOTSET,
            issues,
            (),
            RowCount(sum(validation.total_rows.value for validation in validations) + sum(attack_counts)),
            RowCount(0),
            RowCount(0),
            ValidationIssueCount(len(issues)),
            AvailabilityStatus.AVAILABLE,
        )


def _expected_assets(
    benign_paths: tuple[Path, ...],
    attack_paths: tuple[Path, ...],
    validations: tuple[ChronologyValidation, ...],
) -> tuple[CanonicalAssetLayout[EdgeAssetRole], ...]:
    benign_identities = tuple(benign_sensor_group(path).value for path in benign_paths)
    static_assets = named_assets(_STATIC_BENIGN_BRANCH, EdgeAssetRole.STATIC_BENIGN, benign_identities)
    temporal_identities = tuple(
        identity
        for identity, validation in zip(benign_identities, validations, strict=True)
        if validation.temporal_eligible
    )
    temporal_assets = (
        named_assets(_TEMPORAL_BENIGN_BRANCH, EdgeAssetRole.TEMPORAL_BENIGN, temporal_identities)
        if temporal_identities
        else (empty_asset(_TEMPORAL_BENIGN_BRANCH, EdgeAssetRole.TEMPORAL_BENIGN),)
    )
    attack_assets = named_assets(
        _UNASSIGNED_ATTACK_BRANCH,
        EdgeAssetRole.UNASSIGNED_ATTACK,
        tuple(path.stem for path in attack_paths),
    )
    return static_assets + temporal_assets + attack_assets


def _with_capture_timeline(
    csv_path: Path,
    frame: pl.LazyFrame,
    timeline_path: Path,
    evidence: PcapChronology,
) -> pl.LazyFrame:
    if not evidence.validation.temporal_eligible:
        return frame
    offset = evidence.validation.alignment_offset_microseconds
    if offset is None:
        raise ValueError("verified Edge chronology must retain its display offset")
    write_capture_timeline(csv_path, evidence.pcap_path, timeline_path, offset)
    return (
        frame.drop(EdgeCanonicalColumn.CAPTURE_TIMESTAMP)
        .join(pl.scan_parquet(timeline_path), on=CanonicalProvenanceColumn.SOURCE_ROW_INDEX, how="left")
        .select(tuple(column.name for column in EDGE_SCHEMA.columns))
    )


def _write_static_assets(
    canonical_root: Path,
    timeline_root: Path,
    inputs: _EdgePublicationInputs,
) -> tuple[CanonicalAsset[EdgeAssetRole], ...]:
    enriched_benign = tuple(
        _with_capture_timeline(path, frame, timeline_root / f"{index:05d}.parquet", evidence)
        for index, (path, frame, evidence) in enumerate(
            zip(inputs.benign_paths, inputs.benign_frames, inputs.chronology, strict=True)
        )
    )
    return tuple(
        stream_parquet(frame, canonical_root, asset, EDGE_ARROW_SCHEMA)
        for frame, asset in zip(enriched_benign, inputs.expected_assets[: len(enriched_benign)], strict=True)
    )


def _write_temporal_assets(
    canonical_root: Path,
    static_assets: tuple[CanonicalAsset[EdgeAssetRole], ...],
    inputs: _EdgePublicationInputs,
) -> tuple[CanonicalAsset[EdgeAssetRole], ...]:
    temporal_count = sum(evidence.validation.temporal_eligible for evidence in inputs.chronology) or 1
    temporal_paths = inputs.expected_assets[len(static_assets) : len(static_assets) + temporal_count]
    temporal_frames = tuple(
        pl.scan_parquet(canonical_root / asset.relative_path)
        for asset, evidence in zip(static_assets, inputs.chronology, strict=True)
        if evidence.validation.temporal_eligible
    ) or (pl.scan_parquet(canonical_root / static_assets[0].relative_path).head(0),)
    return tuple(
        stream_parquet(frame, canonical_root, asset, EDGE_ARROW_SCHEMA)
        for frame, asset in zip(temporal_frames, temporal_paths, strict=True)
    )


def _write_attack_assets(
    canonical_root: Path,
    static_assets: tuple[CanonicalAsset[EdgeAssetRole], ...],
    temporal_assets: tuple[CanonicalAsset[EdgeAssetRole], ...],
    inputs: _EdgePublicationInputs,
) -> tuple[CanonicalAsset[EdgeAssetRole], ...]:
    attack_paths = inputs.expected_assets[len(static_assets) + len(temporal_assets) :]
    return tuple(
        stream_parquet(frame, canonical_root, asset, EDGE_ARROW_SCHEMA)
        for frame, asset in zip(inputs.attack_frames, attack_paths, strict=True)
    )
