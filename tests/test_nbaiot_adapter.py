from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from datp_core.catalogue import load_resolved_configuration
from datp_core.catalogue.domain import DatasetDefinition
from datp_core.datasets.adapters.nbaiot import NBaIoTAdapter
from datp_core.datasets.domain import ReadinessStatus
from datp_core.kernel.ids import DatasetId

ROOT = Path(__file__).parents[1]


def test_nbaiot_inspection_is_streaming_deterministic_and_preserves_path_provenance(tmp_path: Path) -> None:
    definition = load_resolved_configuration(ROOT).study.datasets.get(DatasetId("nbaiot"))
    _write_complete_nbaiot_fixture(tmp_path, definition, include_attack=True)

    report = NBaIoTAdapter().inspect(definition, tmp_path)

    assert report.status is ReadinessStatus.READY
    assert report.files == tuple(sorted(report.files))
    assert len(report.source_files) == 10
    assert report.schema is not None
    assert report.schema.expected_field_count == 115
    assert all(manifest.field_count == 115 for manifest in report.source_files)
    assert any("client=Danmini_Doorbell" in manifest.source_role for manifest in report.source_files)
    assert any("family=gafgyt_attacks" in manifest.source_role for manifest in report.source_files)


def test_nbaiot_inspection_blocks_malformed_numeric_rows_and_source_symlinks(tmp_path: Path) -> None:
    definition = load_resolved_configuration(ROOT).study.datasets.get(DatasetId("nbaiot"))
    _write_complete_nbaiot_fixture(tmp_path, definition, include_attack=False)
    root = tmp_path / "N-BaIoT"
    malformed = root / "Danmini_Doorbell" / "benign_traffic.csv"
    lines = malformed.read_text(encoding="utf-8").splitlines()
    fields = lines[1].split(",")
    fields[0] = "not-a-number"
    malformed.write_text("\n".join((lines[0], ",".join(fields))) + "\n", encoding="utf-8")
    symlink_target = root / "Ecobee_Thermostat" / "benign_traffic.csv"
    symlink_target.unlink()
    symlink_target.symlink_to(malformed)

    report = NBaIoTAdapter().inspect(definition, tmp_path)

    assert report.status is ReadinessStatus.BLOCKED
    assert {finding.code for finding in report.findings} >= {"non_numeric_feature", "source_symlink_forbidden"}


def _write_complete_nbaiot_fixture(tmp_path: Path, definition: DatasetDefinition, *, include_attack: bool) -> None:
    # The test uses the resolved authored definition, so it catches config/schema
    # drift rather than maintaining a second hard-coded 115-column fixture.
    field_schema = definition.field_schema
    source_layout = definition.source_layout
    model_features = field_schema["model_features"]
    assert isinstance(model_features, Mapping)
    header_values = model_features["order"]
    assert isinstance(header_values, tuple)
    header_parts: list[str] = []
    for field in header_values:
        assert isinstance(field, str)
        header_parts.append(field)
    header = tuple(header_parts)
    root_name = source_layout["root"]
    benign_name = source_layout["benign_file"]
    device_values = source_layout["device_dirs"]
    assert isinstance(root_name, str)
    assert isinstance(benign_name, str)
    assert isinstance(device_values, tuple)
    devices: list[str] = []
    for device in device_values:
        assert isinstance(device, str)
        devices.append(device)
    root = tmp_path / root_name
    for device in devices:
        device_path = root / device
        device_path.mkdir(parents=True, exist_ok=True)
        _write_csv(device_path / benign_name, header)
    if include_attack:
        attack_path = root / "Danmini_Doorbell" / "gafgyt_attacks" / "combo.csv"
        attack_path.parent.mkdir()
        _write_csv(attack_path, header)


def _write_csv(path: Path, header: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerow(["0.0"] * len(header))
