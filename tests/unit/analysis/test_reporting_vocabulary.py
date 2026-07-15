from datp_core.application.reporting.tracing import RenderingStatus
from datp_core.domain.experiments.protocols import FigureType, ReportArtifactType, TableType


def test_report_artifact_table_and_figure_vocabularies_match_the_architecture() -> None:
    assert tuple(ReportArtifactType) == (
        ReportArtifactType.MAIN_TABLE,
        ReportArtifactType.SUPPLEMENT_TABLE,
        ReportArtifactType.FIGURE,
        ReportArtifactType.WORDING_BLOCK,
    )
    assert tuple(TableType) == (
        TableType.CONFIRMATORY_INTERVAL,
        TableType.DISPERSION_LADDER,
        TableType.SENSITIVITY_GRID,
        TableType.COMPARATOR,
        TableType.STRESS_TEST,
        TableType.CLUSTER_STABILITY,
        TableType.CONTINGENCY,
        TableType.BOUNDARY_NULL,
        TableType.ALERT_BURDEN,
        TableType.COMMUNICATION_STORAGE_COST,
    )
    assert tuple(FigureType) == (
        FigureType.CDF_OVERLAY,
        FigureType.SCATTER,
        FigureType.HEATMAP,
        FigureType.LAMBDA_CURVE,
        FigureType.RECOVERY_CURVE,
        FigureType.SEVERITY_TREND,
    )


def test_figure_type_has_no_sankey_or_flow_diagram_variant() -> None:
    forbidden_terms = ("sankey", "flow")
    assert all(
        all(term not in member.name.lower() and term not in member.value for term in forbidden_terms)
        for member in FigureType
    )


def test_rendering_status_is_closed() -> None:
    assert tuple(RenderingStatus) == (
        RenderingStatus.PENDING,
        RenderingStatus.RENDERED,
        RenderingStatus.TRACE_REFUSED,
    )
