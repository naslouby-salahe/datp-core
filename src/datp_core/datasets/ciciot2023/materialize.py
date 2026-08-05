"""Canonical materialization for audited CICIoT2023 merged sources."""

from pathlib import Path

import polars as pl

from datp_core.datasets.canonical_cache import (
    CanonicalAsset,
    CanonicalReuseRequest,
    canonical_directory,
    reuse_published_canonical,
)
from datp_core.datasets.contracts import (
    CanonicalAssetRole,
    DatasetValidationCode,
    DatasetValidationIssue,
    DatasetValidationReport,
    MaterializedDataset,
    RawDatasetInventory,
    SourceFileRole,
    ValidationSeverity,
)
from datp_core.datasets.materialization import (
    CanonicalPublication,
    canonical_data_partition_assets,
    publish_canonical,
    raw_inventory,
    raw_source_file,
    stream_parquet,
)
from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values import (
    RowCount,
    ValidationIssueCount,
)

from .reader import CICIoT2023AuditSummary, CICIoT2023Reader
from .schema import (
    CICIOT2023_ARROW_SCHEMA,
    CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
    CICIOT2023_SCHEMA,
    CICIoT2023ArtifactName,
    source_relative_path,
)

_CICIOT2023_CANONICALIZATION_CONTRACT = "lossless_model_input_eligibility_evidence"


class CICIoT2023Materializer:
    """Publish lossless merged-file partitions with their eligibility audit."""

    def canonical_directory(self, canonical_root: Path) -> Path:
        return canonical_directory(canonical_root, CICIOT2023_SCHEMA)

    def publish(self, raw_root: Path, canonical_root: Path) -> MaterializedDataset:
        sources = tuple(sorted(raw_root.glob(f"**/{CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY}/*.csv")))
        return self.materialize(sources, canonical_root)

    def materialize(self, source_paths: tuple[Path, ...], canonical_root: Path) -> MaterializedDataset:
        ordered_paths = tuple(sorted(source_paths))
        reusable = reuse_published_canonical(
            CanonicalReuseRequest(
                canonical_root=canonical_root,
                schema=CICIOT2023_SCHEMA,
                canonicalization_contract=_CICIOT2023_CANONICALIZATION_CONTRACT,
                source_paths=ordered_paths,
                source_path_resolver=source_relative_path,
                asset_role_type=CanonicalAssetRole,
                eligibility_policy=CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
            )
        )
        if reusable is not None:
            return reusable
        frames, inventory, report = self.audit(source_paths)
        expected_assets = canonical_data_partition_assets(len(frames))

        def write_assets(data_root: Path) -> tuple[CanonicalAsset, ...]:
            return tuple(
                stream_parquet(frame, data_root, asset, CICIOT2023_ARROW_SCHEMA)
                for frame, asset in zip(frames, expected_assets, strict=True)
            )

        return publish_canonical(
            CanonicalPublication(
                canonical_root,
                _CICIOT2023_CANONICALIZATION_CONTRACT,
                CICIOT2023_SCHEMA,
                inventory,
                report,
                expected_assets,
                write_assets,
                source_paths=ordered_paths,
                source_path_resolver=source_relative_path,
                eligibility_policy=CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
            )
        )

    @staticmethod
    def audit(
        source_paths: tuple[Path, ...],
    ) -> tuple[tuple[pl.LazyFrame, ...], RawDatasetInventory, DatasetValidationReport]:
        if not source_paths:
            raise ValueError("CICIoT2023 materialization requires accepted merged sources")
        ordered_paths, frames, summaries = _audited_sources(source_paths)
        return frames, _source_inventory(ordered_paths, summaries), _validation_report(summaries)


def _audited_sources(
    source_paths: tuple[Path, ...],
) -> tuple[tuple[Path, ...], tuple[pl.LazyFrame, ...], tuple[CICIoT2023AuditSummary, ...]]:
    reader = CICIoT2023Reader()
    ordered_paths = tuple(sorted(source_paths))
    frames = tuple(reader.read(path) for path in ordered_paths)
    summaries = tuple(reader.audit_summary(frame) for frame in frames)
    return ordered_paths, frames, summaries


def _source_inventory(paths: tuple[Path, ...], summaries: tuple[CICIoT2023AuditSummary, ...]) -> RawDatasetInventory:
    sources = tuple(
        raw_source_file(DatasetId.CICIOT2023, path, SourceFileRole.MERGED, summary.total_rows, source_relative_path)
        for path, summary in zip(paths, summaries, strict=True)
    )
    return raw_inventory(DatasetId.CICIOT2023, sources)


def _validation_report(summaries: tuple[CICIoT2023AuditSummary, ...]) -> DatasetValidationReport:
    invalid_labels = RowCount(sum(summary.missing_or_unrecognized_labels.value for summary in summaries))
    nonfinite_features = RowCount(sum(summary.nonfinite_feature_rows.value for summary in summaries))
    infinite_rates = RowCount(sum(summary.infinite_rates.value for summary in summaries))
    empty_rates = RowCount(sum(summary.empty_rates.value for summary in summaries))
    ineligible_rows = RowCount(sum(summary.total_rows.value - summary.eligible_rows.value for summary in summaries))
    issues = _validation_issues(invalid_labels, nonfinite_features, infinite_rates, empty_rates)
    return DatasetValidationReport(
        DatasetId.CICIOT2023,
        issues,
        (),
        RowCount(sum(summary.total_rows.value for summary in summaries)),
        RowCount(0),
        ineligible_rows,
        ValidationIssueCount(sum(issue.severity is ValidationSeverity.WARNING for issue in issues)),
        AvailabilityStatus.AVAILABLE if not issues else AvailabilityStatus.UNAVAILABLE,
    )


def _validation_issues(
    invalid_labels: RowCount, nonfinite_features: RowCount, infinite_rates: RowCount, empty_rates: RowCount
) -> tuple[DatasetValidationIssue, ...]:
    issues: tuple[DatasetValidationIssue, ...] = ()
    for issue in (
        _label_issue(invalid_labels),
        _nonfinite_feature_issue(nonfinite_features),
        _infinite_rate_issue(infinite_rates),
        _empty_rate_issue(empty_rates),
    ):
        if issue is not None:
            issues += (issue,)
    return issues


def _label_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.UNRECOGNIZED_OR_EMPTY_LABEL,
        "Merged rows contain empty or unrecognized labels.",
    )


def _infinite_rate_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.INFINITE_RATE,
        "Lossless canonical data retain infinite Rate values; model-input eligibility excludes non-finite features.",
    )


def _nonfinite_feature_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.NONFINITE_MODEL_INPUT_FEATURE,
        "Lossless canonical data retain non-finite features; model-input eligibility excludes affected rows.",
    )


def _empty_rate_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.EMPTY_RATE,
        "Lossless canonical data retain empty Rate values; model-input eligibility excludes non-finite features.",
    )


def _validation_issue(
    affected_count: RowCount, code: DatasetValidationCode, reason: str
) -> DatasetValidationIssue | None:
    if affected_count.value == 0:
        return None
    return DatasetValidationIssue(
        ValidationSeverity.ERROR,
        code,
        DatasetId.CICIOT2023,
        CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY,
        reason,
        affected_count,
    )
