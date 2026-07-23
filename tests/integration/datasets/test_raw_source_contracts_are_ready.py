"""Read-only smoke audits for the configured external raw-data source tree."""

from datp_core.bootstrap import build_application
from datp_core.pipeline.identifiers import DatasetId


def test_raw_symlink_resolves_to_the_runtime_raw_data_root() -> None:
    config = build_application().config
    raw_link = config.paths.repository_root / "data" / "raw"
    assert raw_link.is_symlink()
    assert raw_link.resolve() == config.paths.raw_data


def test_all_configured_raw_dataset_contracts_are_readable_and_ready() -> None:
    app = build_application()
    reports = tuple(
        app.audit_dataset.execute(app.config.datasets[DatasetId(dataset_id)])
        for dataset_id in ("nbaiot", "ciciot2023", "edge_iiotset")
    )
    assert all(report.ready_for_materialization for report in reports)
    assert all(report.file_count > 0 for report in reports)
    assert all(tree.file_count == tree.header_count for report in reports for tree in report.source_trees)
    assert all(tree.headers_identical for report in reports for tree in report.source_trees)
