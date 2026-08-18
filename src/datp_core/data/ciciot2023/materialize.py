from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.core.identifiers import (
    AvailabilityStatus,
    CanonicalizationContractName,
    DatasetId,
    ValidationReasonText,
    ValidationSourceContext,
)
from datp_core.core.numeric import LogicalElementCount, RowCount, ValidationIssueCount
from datp_core.data.contracts import (
    CanonicalAssetRole,
    DatasetValidationCode,
    DatasetValidationIssue,
    DatasetValidationReport,
    ExclusionReason,
    MaterializedDataset,
    RawDatasetInventory,
    SourceFileRole,
    ValidationSeverity,
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

from .reader import CICIoT2023AuditSummary, CICIoT2023Reader
from .schema import (
    CICIOT2023_ARROW_SCHEMA,
    CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
    CICIOT2023_SCHEMA,
    CICIoT2023ArtifactName,
    CICIoT2023EligibilityReason,
    excluded_source_relative_path,
    source_relative_path,
)

_CICIOT2023_CANONICALIZATION_CONTRACT = CanonicalizationContractName("lossless_model_input_eligibility_evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class CICIoT2023AuditResult:
    frames: tuple[pl.LazyFrame, ...]
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport


@dataclass(frozen=True, slots=True, kw_only=True)
class _AuditedCICIoT2023Sources:
    paths: tuple[Path, ...]
    frames: tuple[pl.LazyFrame, ...]
    summaries: tuple[CICIoT2023AuditSummary, ...]


class CICIoT2023Materializer:
    def canonical_directory(self, canonical_root: Path) -> Path:
        return canonical_directory(canonical_root, CICIOT2023_SCHEMA)

    def publish(
        self,
        raw_root: Path,
        canonical_root: Path,
        *,
        progress: MaterializationProgress | None = None,
    ) -> MaterializedDataset[CanonicalAssetRole, CICIoT2023EligibilityReason]:
        sources = tuple(sorted(raw_root.glob(f"**/{CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY}/*.csv")))
        all_csvs = tuple(sorted(raw_root.glob("**/*.csv")))
        excluded_paths = tuple(path for path in all_csvs if path not in frozenset(sources))
        return self.materialize(sources, canonical_root, excluded_paths=excluded_paths, progress=progress)

    def materialize(
        self,
        source_paths: tuple[Path, ...],
        canonical_root: Path,
        *,
        excluded_paths: tuple[Path, ...] = (),
        progress: MaterializationProgress | None = None,
    ) -> MaterializedDataset[CanonicalAssetRole, CICIoT2023EligibilityReason]:
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
    ) -> CanonicalPublication[CanonicalAssetRole, CICIoT2023EligibilityReason]:
        audit = CICIoT2023Materializer.audit(
            source_paths,
            excluded_paths=excluded_paths,
            progress=progress,
        )
        expected_assets = canonical_data_partition_assets(LogicalElementCount(len(audit.frames)))

        def write_assets(data_root: Path) -> tuple[CanonicalAsset[CanonicalAssetRole], ...]:
            written: list[CanonicalAsset[CanonicalAssetRole]] = []
            for index, (frame, asset) in enumerate(zip(audit.frames, expected_assets, strict=True)):
                if progress is not None:
                    progress(
                        f"ciciot2023 writing canonical asset {index + 1}/{len(expected_assets)} {asset.relative_path}"
                    )
                written.append(stream_parquet(frame, data_root, asset, CICIOT2023_ARROW_SCHEMA))
            return tuple(written)

        return CanonicalPublication(
            canonical_root=canonical_root,
            canonicalization_contract=_CICIOT2023_CANONICALIZATION_CONTRACT,
            schema=CICIOT2023_SCHEMA,
            inventory=audit.inventory,
            validation_report=audit.validation_report,
            expected_assets=expected_assets,
            writer=write_assets,
            eligibility_policy=CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
        )

    @staticmethod
    def audit(
        source_paths: tuple[Path, ...],
        *,
        excluded_paths: tuple[Path, ...] = (),
        progress: MaterializationProgress | None = None,
    ) -> CICIoT2023AuditResult:
        audited_sources = _audited_sources(source_paths, progress=progress)
        return CICIoT2023AuditResult(
            frames=audited_sources.frames,
            inventory=_source_inventory(
                audited_sources.paths,
                audited_sources.summaries,
                excluded_paths=excluded_paths,
            ),
            validation_report=_validation_report(audited_sources.summaries),
        )


def _audited_sources(
    source_paths: tuple[Path, ...],
    *,
    progress: MaterializationProgress | None = None,
) -> _AuditedCICIoT2023Sources:
    reader = CICIoT2023Reader()
    ordered_paths = tuple(sorted(source_paths))
    frames: list[pl.LazyFrame] = []
    for index, path in enumerate(ordered_paths):
        if progress is not None:
            progress(f"ciciot2023 reading source {index + 1}/{len(ordered_paths)} {path.name}")
        frames.append(reader.read(path))
    summaries = tuple(reader.audit_summary(frame) for frame in frames)
    return _AuditedCICIoT2023Sources(
        paths=ordered_paths,
        frames=tuple(frames),
        summaries=summaries,
    )


def _source_inventory(
    paths: tuple[Path, ...],
    summaries: tuple[CICIoT2023AuditSummary, ...],
    *,
    excluded_paths: tuple[Path, ...] = (),
) -> RawDatasetInventory:
    sources = tuple(
        raw_source_file(DatasetId.CICIOT2023, path, SourceFileRole.MERGED, summary.total_rows, source_relative_path)
        for path, summary in zip(paths, summaries, strict=True)
    )
    return raw_inventory(
        DatasetId.CICIOT2023,
        sources,
        excluded_sources=tuple(
            excluded_source_file(
                DatasetId.CICIOT2023,
                path,
                ExclusionReason.UNRECOGNIZED_SOURCE,
                excluded_source_relative_path,
            )
            for path in excluded_paths
        ),
    )


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
    invalid_labels: RowCount,
    nonfinite_features: RowCount,
    infinite_rates: RowCount,
    empty_rates: RowCount,
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
        ValidationReasonText("Merged rows contain empty or unrecognized labels."),
    )


def _infinite_rate_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.INFINITE_RATE,
        ValidationReasonText(
            "Lossless canonical data retain infinite Rate values; model-input eligibility excludes non-finite features."
        ),
    )


def _nonfinite_feature_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.NONFINITE_MODEL_INPUT_FEATURE,
        ValidationReasonText(
            "Lossless canonical data retain non-finite features; model-input eligibility excludes affected rows."
        ),
    )


def _empty_rate_issue(affected_count: RowCount) -> DatasetValidationIssue | None:
    return _validation_issue(
        affected_count,
        DatasetValidationCode.EMPTY_RATE,
        ValidationReasonText(
            "Lossless canonical data retain empty Rate values; model-input eligibility excludes non-finite features."
        ),
    )


def _validation_issue(
    affected_count: RowCount,
    code: DatasetValidationCode,
    reason: ValidationReasonText,
) -> DatasetValidationIssue | None:
    if affected_count.value == 0:
        return None
    return DatasetValidationIssue(
        ValidationSeverity.ERROR,
        code,
        DatasetId.CICIOT2023,
        ValidationSourceContext(CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY),
        reason,
        affected_count,
    )
