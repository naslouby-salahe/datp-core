"""Miniature deterministic population fixtures."""

from datetime import UTC
from pathlib import Path

import polars as pl
import pytest

from datp_core.datasets.edge_iiotset.schema import (
    EDGE_BENIGN_SENSOR_GROUPS,
    EDGE_NUMERIC_FEATURE_COLUMNS,
    EdgeSensorGroup,
)
from datp_core.datasets.nbaiot.schema import NBAIOT_DEVICE_FAMILIES, NBAIOT_DEVICE_IDENTITIES, NBaIoTDeviceFamily
from datp_core.domain.values.checksums import Checksum


def _family_for(device: str) -> str:
    mapping = {
        "danmini_doorbell": NBaIoTDeviceFamily.DOORBELL.value,
        "ecobee_thermostat": NBaIoTDeviceFamily.THERMOSTAT.value,
        "ennio_doorbell": NBaIoTDeviceFamily.DOORBELL.value,
        "philips_b120n10_baby_monitor": NBaIoTDeviceFamily.BABY_MONITOR.value,
        "provision_pt_737e_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
        "provision_pt_838_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
        "samsung_snh_1011_n_webcam": NBaIoTDeviceFamily.WEBCAM.value,
        "simplehome_xcs7_1002_wht_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
        "simplehome_xcs7_1003_wht_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
    }
    return mapping[device]


@pytest.fixture
def nbaiot_canonical_root(tmp_path: Path) -> Path:
    root = tmp_path / "nbaiot"
    data = root / "data"
    data.mkdir(parents=True)
    rows: list[dict[str, str | int | float | bool | None]] = []
    index = 0
    for device in NBAIOT_DEVICE_IDENTITIES:
        for label, count in (("benign", 30), ("attack", 12)):
            for local in range(count):
                rows.append(
                    {
                        "physical_client_id": device,
                        "physical_device_family": _family_for(device),
                        "raw_label": label,
                        "attack_family": None if label == "benign" else "mirai",
                        "attack_subtype": None if label == "benign" else "udp",
                        "source_path": f"{device}/{label}_{local}.csv",
                        "source_row_index": local,
                        "stable_row_id": f"{device}:{label}:{local}",
                        "MI_dir_L5_weight": float(local),
                    }
                )
                index += 1
    pl.DataFrame(rows).write_parquet(data / "part-00000.parquet")
    return root


@pytest.fixture
def ciciot_canonical_root(tmp_path: Path) -> Path:
    root = tmp_path / "ciciot2023"
    data = root / "data"
    data.mkdir(parents=True)
    rows: list[dict[str, str | int | float | bool | None]] = []
    for file_index in range(1, 64):
        client = f"Merged{file_index:02d}"
        source = f"MERGED_CSV/{client}.csv"
        for local in range(9):
            label = "BENIGN" if local < 6 else "DDOS-TCP_FLOOD"
            eligible = local != 8 or file_index != 1
            rows.append(
                {
                    "label": label,
                    "raw_label": label,
                    "model_input_eligible": eligible,
                    "missing_or_unrecognized_label": False,
                    "nonfinite_feature": not eligible,
                    "source_path": source,
                    "source_row_index": local,
                    "stable_row_id": f"{client}:{local}",
                    "rate": 1.0 if eligible else float("inf"),
                }
            )
    pl.DataFrame(rows).write_parquet(data / "part-00000.parquet")
    return root


@pytest.fixture
def edge_canonical_root(tmp_path: Path) -> Path:
    root = tmp_path / "edge_iiotset"
    static = root / "data" / "static_benign"
    temporal = root / "data" / "temporal_benign"
    static.mkdir(parents=True)
    temporal.mkdir(parents=True)
    chronology = []
    for group in EDGE_BENIGN_SENSOR_GROUPS:
        rows = []
        for local in range(12):
            rows.append(
                {
                    "benign_sensor_group": group,
                    "source_folder": group,
                    "source_path": f"Normal traffic/{group}/{group}.csv",
                    "source_row_index": local,
                    "stable_row_id": f"{group}:{local}",
                    "capture_timestamp": None,
                    "raw_timestamp": f"2021 00:00:{local:02d}.000000000",
                    "attack_label": "0",
                    "attack_type": "Normal",
                }
            )
        pl.DataFrame(rows).write_parquet(static / f"{group}.parquet")
        eligible = group is not EdgeSensorGroup.MODBUS
        chronology.append(
            {
                "alignment_offset_microseconds": 0 if eligible else None,
                "alignment_verified": eligible,
                "duplicate_timestamp_count": 0,
                "evidence_row_count": 12 if eligible else None,
                "evidence_source_path": f"Normal traffic/{group}/{group}.pcap" if eligible else None,
                "group_identity": group,
                "invalid_rows": 0,
                "is_monotonic": False,
                "parseable_rows": 12,
                "reason": "PCAP alignment is verified, but matched capture timestamps are not monotonic."
                if eligible
                else "PCAP alignment could not be verified: Edge CSV frame.time is not a capture-clock value",
                "skipped_evidence_rows": 0,
                "status": "available" if eligible else "unavailable",
                "temporal_eligible": False,
                "total_rows": 12,
                "trailing_evidence_rows": 0,
            }
        )
    pl.DataFrame(schema={"x": pl.Int64}).clear().write_parquet(temporal / "empty.parquet")
    import json

    manifest = {
        "assets": [],
        "canonicalization_contract": "pcap_verified_source_order_and_typed_asset_roles",
        "chronology": chronology,
        "dataset": "edge_iiotset",
        "inventory": {
            "accepted_row_count": 0,
            "accepted_source_count": 0,
            "checksum": "0" * 64,
            "excluded_source_count": 0,
            "sources": [],
        },
        "schema_checksum": EDGE_SCHEMA_CHECKSUM.value,
        "validation_report": {
            "accepted_rows": 0,
            "excluded_rows": 0,
            "exclusions": [],
            "invalid_rows": 0,
            "issues": [],
            "status": "available",
            "warning_count": 0,
        },
    }
    (root / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


@pytest.fixture
def edge_temporal_eligible_root(tmp_path: Path) -> Path:
    """Edge corpus with nine chronology-eligible groups and capture timestamps."""
    root = tmp_path / "edge_temporal_ok"
    static = root / "data" / "static_benign"
    temporal = root / "data" / "temporal_benign"
    static.mkdir(parents=True)
    temporal.mkdir(parents=True)
    chronology = []
    from datetime import datetime

    for group in EDGE_BENIGN_SENSOR_GROUPS:
        eligible = group is not EdgeSensorGroup.MODBUS
        rows = []
        for local in range(20):
            ts = datetime(2021, 1, 1, 0, 0, local, tzinfo=UTC) if eligible else None
            rows.append(
                {
                    "benign_sensor_group": group,
                    "source_folder": group,
                    "source_path": f"Normal traffic/{group}/{group}.csv",
                    "source_row_index": local,
                    "stable_row_id": f"{group}:{local}",
                    "capture_timestamp": ts,
                    "raw_timestamp": f"2021 00:00:{local:02d}.000000000",
                    "attack_label": "0",
                    "attack_type": "Normal",
                    **{feature: "0" for feature in EDGE_NUMERIC_FEATURE_COLUMNS},
                }
            )
        frame = pl.DataFrame(rows)
        frame.write_parquet(static / f"{group}.parquet")
        if eligible:
            frame.write_parquet(temporal / f"{group}.parquet")
        chronology.append(
            {
                "alignment_offset_microseconds": 0 if eligible else None,
                "alignment_verified": eligible,
                "duplicate_timestamp_count": 1 if eligible else 0,
                "evidence_row_count": 20 if eligible else None,
                "evidence_source_path": f"Normal traffic/{group}/{group}.pcap" if eligible else None,
                "group_identity": group,
                "invalid_rows": 0,
                "is_monotonic": eligible,
                "parseable_rows": 20,
                "reason": "Every CSV row is an ordered PCAP subsequence match after its verified display offset."
                if eligible
                else "PCAP alignment could not be verified: Edge CSV frame.time is not a capture-clock value",
                "skipped_evidence_rows": 0,
                "status": "available" if eligible else "unavailable",
                "temporal_eligible": eligible,
                "total_rows": 20,
                "trailing_evidence_rows": 0,
            }
        )
    import json

    manifest = {
        "assets": [],
        "canonicalization_contract": "pcap_verified_source_order_and_typed_asset_roles",
        "chronology": chronology,
        "dataset": "edge_iiotset",
        "inventory": {
            "accepted_row_count": 0,
            "accepted_source_count": 0,
            "checksum": "0" * 64,
            "excluded_source_count": 0,
            "sources": [],
        },
        "schema_checksum": EDGE_SCHEMA_CHECKSUM.value,
        "validation_report": {
            "accepted_rows": 0,
            "excluded_rows": 0,
            "exclusions": [],
            "invalid_rows": 0,
            "issues": [],
            "status": "available",
            "warning_count": 0,
        },
    }
    (root / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


# Schema checksum is validated only as opaque string in population manifests for Edge tests.
EDGE_SCHEMA_CHECKSUM = Checksum("a" * 64)
_ = NBAIOT_DEVICE_FAMILIES
