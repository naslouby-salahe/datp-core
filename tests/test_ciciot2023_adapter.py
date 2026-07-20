from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from datp_core.catalogue import load_resolved_configuration
from datp_core.catalogue.domain import DatasetDefinition
from datp_core.datasets.adapters import Ciciot2023Adapter
from datp_core.datasets.domain import ReadinessStatus
from datp_core.kernel.ids import DatasetId

ROOT = Path(__file__).parents[1]


def test_ciciot_inspection_keeps_reference_files_out_of_executable_rows(tmp_path: Path) -> None:
    definition = load_resolved_configuration(ROOT).study.datasets.get(DatasetId("ciciot2023"))
    feature_names = _feature_names(definition)

    merged = tmp_path / "CIC_IOT_Dataset2023/CSV/MERGED_CSV/Merged-01.csv"
    reference = tmp_path / "CIC_IOT_Dataset2023/CSV/CSV/Benign/fixture.pcap.csv"
    merged.parent.mkdir(parents=True)
    reference.parent.mkdir(parents=True)
    _write_csv(merged, feature_names + ("Label",), (("1",) * 39 + ("BENIGN",), ("2",) * 39 + ("Attack",)))
    _write_csv(reference, feature_names, (("reference-only",) * 39,))

    report = Ciciot2023Adapter().inspect(definition, tmp_path, max_files=1)

    assert report.status is ReadinessStatus.READY
    assert tuple(manifest.source_role for manifest in report.source_files) == ("reference_only", "executable")
    assert {finding.code for finding in report.findings} >= {
        "pseudo_client_identity",
        "reference_source_schema_only",
        "row_identity_provenance",
    }
    assert all(
        "joined" not in finding.message or finding.code == "reference_source_schema_only" for finding in report.findings
    )


def test_ciciot_rejects_nonfinite_executable_numeric_rows(tmp_path: Path) -> None:
    definition = load_resolved_configuration(ROOT).study.datasets.get(DatasetId("ciciot2023"))
    feature_names = _feature_names(definition)
    merged = tmp_path / "CIC_IOT_Dataset2023/CSV/MERGED_CSV/Merged-01.csv"
    reference = tmp_path / "CIC_IOT_Dataset2023/CSV/CSV/Benign/fixture.pcap.csv"
    merged.parent.mkdir(parents=True)
    reference.parent.mkdir(parents=True)
    _write_csv(merged, feature_names + ("Label",), (("nan",) + ("1",) * 38 + ("BENIGN",),))
    _write_csv(reference, feature_names, (("not-parsed",) * 39,))

    report = Ciciot2023Adapter().inspect(definition, tmp_path)

    assert report.status is ReadinessStatus.BLOCKED
    assert "unparseable_numeric_feature" in {finding.code for finding in report.findings}


def test_ciciot_discovers_matching_files_by_relative_path(tmp_path: Path) -> None:
    definition = load_resolved_configuration(ROOT).study.datasets.get(DatasetId("ciciot2023"))
    feature_names = _feature_names(definition)
    merged_root = tmp_path / "CIC_IOT_Dataset2023/CSV/MERGED_CSV"
    reference = tmp_path / "CIC_IOT_Dataset2023/CSV/CSV/Benign/fixture.pcap.csv"
    merged_root.mkdir(parents=True)
    reference.parent.mkdir(parents=True)
    for name in ("Merged-z.csv", "Merged-a.csv"):
        _write_csv(merged_root / name, feature_names + ("Label",), (("1",) * 39 + ("BENIGN",),))
    _write_csv(reference, feature_names, (("reference-only",) * 39,))

    report = Ciciot2023Adapter().inspect(definition, tmp_path)

    assert report.status is ReadinessStatus.READY
    assert report.files == tuple(sorted(report.files))


def _write_csv(path: Path, header: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _feature_names(definition: DatasetDefinition) -> tuple[str, ...]:
    features = definition.field_schema["model_features"]
    assert isinstance(features, Mapping)
    order = features["order"]
    assert isinstance(order, tuple)
    assert all(isinstance(value, str) for value in order)
    names = tuple(value for value in order if isinstance(value, str))
    assert len(names) == 39
    return names
