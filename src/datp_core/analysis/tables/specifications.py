from dataclasses import dataclass

from datp_core.analysis.report_models import ReportColumn, ReportRow, TableSpecification
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.operating_points import (
    ConformalCoverageResult,
    EligibilityCoverageResult,
    PolicyEvaluationResult,
    ValidCvResult,
)
from datp_core.domain.experiments.protocols import TableType


@dataclass(frozen=True, slots=True, kw_only=True)
class EligibilityCoverageTableSpecification:
    table: TableSpecification
    eligibility_coverage: EligibilityCoverageResult

    def __post_init__(self) -> None:
        _validate_coverage_table_specification(
            self.table,
            self.eligibility_coverage,
            EligibilityCoverageResult,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConformalCoverageTableSpecification:
    table: TableSpecification
    conformal_coverage: ConformalCoverageResult

    def __post_init__(self) -> None:
        _validate_coverage_table_specification(
            self.table,
            self.conformal_coverage,
            ConformalCoverageResult,
        )


def confirmatory_interval_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.CONFIRMATORY_INTERVAL, columns, rows)


def dispersion_ladder_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.DISPERSION_LADDER, columns, rows)


def sensitivity_grid_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.SENSITIVITY_GRID, columns, rows)


def comparator_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.COMPARATOR, columns, rows)


def stress_test_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.STRESS_TEST, columns, rows)


def cluster_stability_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.CLUSTER_STABILITY, columns, rows)


def contingency_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.CONTINGENCY, columns, rows)


def boundary_null_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.BOUNDARY_NULL, columns, rows)


def alert_burden_table(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return _table(TableType.ALERT_BURDEN, columns, rows)


def communication_storage_cost_table(
    columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]
) -> TableSpecification:
    return _table(TableType.COMMUNICATION_STORAGE_COST, columns, rows)


def policy_evaluation_summary_table(result: PolicyEvaluationResult) -> EligibilityCoverageTableSpecification:
    coverage = result.fleet_dispersion.eligibility_coverage
    table = dispersion_ladder_table(
        (
            ReportColumn(key="policy", label="Policy"),
            ReportColumn(key="cv_fpr", label="CV(FPR)"),
            ReportColumn(key="iqr_fpr", label="IQR(FPR)"),
            ReportColumn(key="fpr_range", label="FPR range"),
            ReportColumn(key="worst_client_fpr", label="Worst-client FPR"),
            ReportColumn(key="eligible_clients", label="Eligible clients"),
            ReportColumn(key="roster_clients", label="Roster clients"),
        ),
        (
            ReportRow(
                values=(
                    result.policy.value,
                    _cv_fpr_value(result),
                    result.fleet_dispersion.iqr_fpr,
                    result.fleet_dispersion.fpr_range,
                    result.fleet_dispersion.worst_client_fpr.value,
                    coverage.eligible_count,
                    coverage.roster_count,
                )
            ),
        ),
    )
    return EligibilityCoverageTableSpecification(table=table, eligibility_coverage=coverage)


def _table(table_type: TableType, columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> TableSpecification:
    return TableSpecification(table_type=table_type, columns=columns, rows=rows)


def _cv_fpr_value(result: PolicyEvaluationResult) -> float | str:
    cv_fpr = result.fleet_dispersion.cv_fpr
    if isinstance(cv_fpr, ValidCvResult):
        return cv_fpr.point_estimate
    return cv_fpr.reason


def _validate_coverage_table_specification(
    table: TableSpecification,
    coverage: object,
    expected_coverage_type: type[EligibilityCoverageResult] | type[ConformalCoverageResult],
) -> None:
    if not _has_coverage_table_components(table, coverage, expected_coverage_type):
        raise DomainValidationError(
            detail="coverage tables require a table and their dedicated typed coverage result",
            value=repr(coverage),
            constraint="TableSpecification and dedicated typed coverage result",
        )


def _has_coverage_table_components(
    table: TableSpecification,
    coverage: object,
    expected_coverage_type: type[EligibilityCoverageResult] | type[ConformalCoverageResult],
) -> bool:
    return type(table) is TableSpecification and type(coverage) is expected_coverage_type
