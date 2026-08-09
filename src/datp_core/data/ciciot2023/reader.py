"""Lazy reader for the audited CICIoT2023 merged artifacts."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.core.identifiers import RawSourceFilename
from datp_core.core.numeric import RowCount
from datp_core.data.materialization import provenance_expressions

from .schema import (
    CICIOT2023_FEATURE_COLUMNS,
    CICIOT2023_LABELS,
    CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
    CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN,
    CICIOT2023_RAW_COLUMNS,
    CICIOT2023_SCHEMA,
    CanonicalProvenanceColumn,
    CICIoT2023ArtifactName,
    CICIoT2023AuditField,
    CICIoT2023Column,
    CICIoT2023EligibilityReason,
    CICIoT2023RawColumn,
    canonical_name,
    is_accepted_merged_source,
    source_relative_path,
)


@dataclass(frozen=True, slots=True)
class CICIoT2023AuditSummary:
    total_rows: RowCount
    missing_or_unrecognized_labels: RowCount
    nonfinite_feature_rows: RowCount
    eligible_rows: RowCount
    infinite_rates: RowCount
    empty_rates: RowCount


class CICIoT2023Reader:
    """Read only merged labelled files while retaining file and row provenance."""

    def read(self, path: Path) -> pl.LazyFrame:
        self._validate_source_path(path)
        return self._canonical_frame(self._source_frame(path), path)

    @staticmethod
    def _validate_source_path(path: Path) -> None:
        if path.parent.name != CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY or not is_accepted_merged_source(
            RawSourceFilename(path.name)
        ):
            raise ValueError("CICIoT2023 accepts only audited merged CSV sources")

    @staticmethod
    def _source_frame(path: Path) -> pl.LazyFrame:
        source = pl.scan_csv(
            path,
            schema=pl.Schema(
                tuple((column, pl.Float64) for column in CICIOT2023_FEATURE_COLUMNS)
                + ((CICIoT2023RawColumn.LABEL, pl.String),)
            ),
            try_parse_dates=False,
        )
        if tuple(source.collect_schema().names()) != CICIOT2023_RAW_COLUMNS:
            raise ValueError("CICIoT2023 source columns differ from the audited order")
        return source

    @staticmethod
    def _canonical_frame(source: pl.LazyFrame, path: Path) -> pl.LazyFrame:
        canonical = source.with_row_index(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).with_columns(
            tuple(pl.col(column).alias(canonical_name(column)) for column in CICIOT2023_FEATURE_COLUMNS)
            + (
                pl.col(CICIoT2023RawColumn.LABEL).alias(CICIoT2023Column.RAW_LABEL),
                pl.col(CICIoT2023RawColumn.LABEL).str.strip_chars().str.to_uppercase().alias(CICIoT2023Column.LABEL),
                pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).cast(pl.UInt64),
                *provenance_expressions(path, source_relative_path),
            )
        )
        return CICIoT2023Reader.model_input_eligibility_audit(canonical).select(
            tuple(column.name for column in CICIOT2023_SCHEMA.columns)
        )

    def audit_summary(self, frame: pl.LazyFrame) -> CICIoT2023AuditSummary:
        summary = frame.select(
            pl.len().alias(CICIoT2023AuditField.TOTAL_ROWS),
            pl.col(CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL)
            .sum()
            .alias(CICIoT2023AuditField.MISSING_OR_UNRECOGNIZED_LABELS),
            pl.col(CICIoT2023EligibilityReason.NONFINITE_FEATURE)
            .sum()
            .alias(CICIoT2023AuditField.NONFINITE_FEATURE_ROWS),
            pl.col(CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN).sum().alias(CICIoT2023AuditField.ELIGIBLE_ROWS),
            pl.col(CICIoT2023Column.RATE).is_infinite().sum().alias(CICIoT2023AuditField.INFINITE_RATES),
            pl.col(CICIoT2023Column.RATE).is_null().sum().alias(CICIoT2023AuditField.EMPTY_RATES),
        ).collect(engine="streaming")
        return CICIoT2023AuditSummary(
            total_rows=RowCount(int(summary.item(0, CICIoT2023AuditField.TOTAL_ROWS))),
            missing_or_unrecognized_labels=RowCount(
                int(summary.item(0, CICIoT2023AuditField.MISSING_OR_UNRECOGNIZED_LABELS))
            ),
            nonfinite_feature_rows=RowCount(int(summary.item(0, CICIoT2023AuditField.NONFINITE_FEATURE_ROWS))),
            eligible_rows=RowCount(int(summary.item(0, CICIoT2023AuditField.ELIGIBLE_ROWS))),
            infinite_rates=RowCount(int(summary.item(0, CICIoT2023AuditField.INFINITE_RATES))),
            empty_rates=RowCount(int(summary.item(0, CICIoT2023AuditField.EMPTY_RATES))),
        )

    @staticmethod
    def model_input_eligibility_audit(frame: pl.LazyFrame) -> pl.LazyFrame:
        missing_label = CICIoT2023Reader._missing_or_unrecognized_label_expression()
        nonfinite_feature = CICIoT2023Reader._nonfinite_feature_expression()
        audited = frame.with_columns(
            missing_label.alias(CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL),
            nonfinite_feature.alias(CICIoT2023EligibilityReason.NONFINITE_FEATURE),
        )
        return audited.with_columns(
            (
                ~(
                    pl.col(CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL)
                    | pl.col(CICIoT2023EligibilityReason.NONFINITE_FEATURE)
                )
            ).alias(CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN),
        )

    @staticmethod
    def _missing_or_unrecognized_label_expression() -> pl.Expr:
        label_column = CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY.label_column
        return pl.col(label_column).is_null() | ~pl.col(label_column).is_in(CICIOT2023_LABELS)

    @staticmethod
    def _nonfinite_feature_expression() -> pl.Expr:
        return pl.any_horizontal(
            tuple(
                ~pl.col(column).is_finite().fill_null(False)
                for column in CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY.feature_columns
            )
        )
