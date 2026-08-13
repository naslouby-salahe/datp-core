import json
from csv import DictReader
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

import datp_core.presentation.export as publication_export
from datp_core.analysis.descriptive import ScoreRole
from datp_core.analysis.preparation import AnalysisDocument
from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.core.identifiers import (
    AvailabilityStatus,
    ClientIdentityToken,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    FigureLabel,
    FigureTitle,
    MetricId,
    PopulationId,
)
from datp_core.core.numeric import MetricValue, Seed, ThresholdValue
from datp_core.presentation.export import (
    PUBLICATION_SOURCE_DATA_FILENAME,
    PUBLICATION_SOURCE_MANIFEST_FILENAME,
    PublicationBundle,
    ReportProvenance,
    export_markdown,
)
from datp_core.presentation.figures import EmpiricalCdfFigureSeries, FigureSpec, ThresholdOverlay
from datp_core.presentation.tables import EvidenceText, PublicationTable, TableCell, TableCellRenderedValue, TableTitle


def test_publication_export_writes_traceable_source_manifest(tmp_path: Path) -> None:
    temporal_source = tmp_path / "temporal_source.csv"
    temporal_source.write_text("seed,value\n0,0.05\n", encoding="utf-8")
    publication = export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                evidence_role=EvidenceRole.CONFIRMATORY,
            ),
            claims=(),
            tables=(
                PublicationTable(
                    title=TableTitle("summary"),
                    cells=(
                        TableCell(
                            metric=MetricId.FALSE_POSITIVE_RATE,
                            availability=AvailabilityStatus.AVAILABLE,
                            rendered_value=TableCellRenderedValue("0.05"),
                            evidence=EvidenceText("held-out"),
                        ),
                    ),
                ),
            ),
            figures=(),
        ),
        tmp_path / "publication.md",
        additional_source_files=(temporal_source,),
    )

    manifest = json.loads((tmp_path / PUBLICATION_SOURCE_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["publication"] == publication.name
    assert manifest["publication_bytes"] == publication.stat().st_size
    assert manifest["publication_sha256"] == sha256(publication.read_bytes()).hexdigest()
    assert manifest["experiment"] == "shared_vs_local_confirmation"
    assert manifest["table_count"] == 1
    assert manifest["claims"] == []
    assert [(source["filename"], source["kind"], source["row_count"]) for source in manifest["sources"]] == [
        (PUBLICATION_SOURCE_DATA_FILENAME, "table_figure_source_data", 1),
        ("temporal_source.csv", "additional_figure_table_source", 1),
    ]
    assert all(len(source["sha256"]) == 64 and source["bytes"] > 0 for source in manifest["sources"])
    rendered = publication.read_text(encoding="utf-8")
    assert "## Calibration terminology" in rendered
    assert "ECE, Brier score, and NLL" in rendered
    with (tmp_path / PUBLICATION_SOURCE_DATA_FILENAME).open(encoding="utf-8", newline="") as stream:
        rows = tuple(DictReader(stream))
    assert rows == (
        {
            "experiment": "shared_vs_local_confirmation",
            "population": "nbaiot_natural_devices",
            "evidence_role": "confirmatory",
            "output_kind": "table",
            "output_title": "summary",
            "series_label": "",
            "metric": "false_positive_rate",
            "availability": "available",
            "value_index": "",
            "x_value": "",
            "y_value": "0.05",
            "point_label": "",
            "evidence": "held-out",
            "unavailable_reason": "",
            "client_id": "",
            "training_seed": "",
            "score_role": "",
            "threshold_method": "",
            "threshold_value": "",
            "benign_exceedance": "",
            "attack_acceptance": "",
            "balanced_accuracy": "",
            "macro_f1": "",
        },
    )


def test_publication_source_data_retains_cdf_execution_identity_and_threshold_overlays(tmp_path: Path) -> None:
    figure = FigureSpec(
        title=FigureTitle("score geometry"),
        empirical_cdf_series=(
            EmpiricalCdfFigureSeries(
                label=FigureLabel("client score CDF"),
                x_metric=MetricId.RECONSTRUCTION_ERROR,
                y_metric=MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY,
                availability=AvailabilityStatus.AVAILABLE,
                x_values=(MetricValue(0.1),),
                y_values=(MetricValue(1.0),),
                client_id=ClientIdentityToken("client_0"),
                seed=Seed(7),
                score_role=ScoreRole.BENIGN_EVALUATION,
                threshold_overlays=(
                    ThresholdOverlay(
                        method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                        value=ThresholdValue(0.2),
                        benign_exceedance=MetricValue(0.1),
                        attack_acceptance=MetricValue(0.3),
                        balanced_accuracy=MetricValue(0.8),
                        macro_f1=MetricValue(0.7),
                    ),
                ),
            ),
        ),
    )
    export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                evidence_role=EvidenceRole.CONFIRMATORY,
            ),
            claims=(),
            tables=(),
            figures=(figure,),
        ),
        tmp_path / "publication.md",
    )

    with (tmp_path / PUBLICATION_SOURCE_DATA_FILENAME).open(encoding="utf-8", newline="") as stream:
        rows = tuple(DictReader(stream))
    cdf, overlay = rows
    assert (cdf["client_id"], cdf["training_seed"], cdf["score_role"]) == (
        "client_0",
        "7",
        "benign_evaluation",
    )
    assert overlay["output_kind"] == "figure_threshold_overlay"
    assert overlay["threshold_method"] == "local_threshold"
    assert overlay["threshold_value"] == "0.20000000000000001"
    assert overlay["macro_f1"] == "0.69999999999999996"


def test_confirmatory_export_registers_the_detailed_analysis_report_as_release_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The manifest must retain per-seed effects, including null and opposite cells."""
    captured: dict[str, tuple[Path, ...]] = {}
    report = tmp_path / "analysis_report.md"

    def write_report(_document: object, destination: Path) -> Path:
        destination.write_text("detailed paired evidence", encoding="utf-8")
        return destination

    def capture_export(
        _bundle: PublicationBundle,
        destination: Path,
        *,
        additional_source_files: tuple[Path, ...] = (),
    ) -> Path:
        captured["sources"] = additional_source_files
        return destination

    table = PublicationTable(
        title=TableTitle("table"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value=TableCellRenderedValue("0.1"),
                evidence=EvidenceText("held-out"),
            ),
        ),
    )
    monkeypatch.setattr(publication_export, "export_analysis_report", write_report)
    monkeypatch.setattr(publication_export, "export_markdown", capture_export)
    monkeypatch.setattr(publication_export, "_interval_table", lambda _interval: table)
    monkeypatch.setattr(publication_export, "_wilcoxon_table", lambda _wilcoxon, _rank: table)
    monkeypatch.setattr(publication_export, "_paired_values_table", lambda _document: table)
    monkeypatch.setattr(publication_export, "_precision_diagnostics_table", lambda _diagnostics: table)
    monkeypatch.setattr(publication_export, "_leave_one_device_out_table", lambda _diagnostics: table)
    monkeypatch.setattr(publication_export, "_mechanism_tables", lambda _mechanisms: ())
    document = SimpleNamespace(
        interval=SimpleNamespace(availability=AvailabilityStatus.AVAILABLE),
        decision=SimpleNamespace(decision=ScientificDecision.NO_OBSERVED_ADVANTAGE, rationale="null result"),
        wilcoxon=object(),
        rank_biserial=object(),
        precision_diagnostics=None,
        leave_one_device_out=None,
        mechanisms=(),
    )

    publication_export.export_confirmatory_publication(
        cast(AnalysisDocument, document),
        tmp_path,
        verified_anchor_gate=None,
    )

    assert captured["sources"] == (report,)
