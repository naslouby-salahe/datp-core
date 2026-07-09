import csv
import json

import pytest

from datp_core.data.nbaiot import (
    NbaiotDataError,
    SampleSource,
    discover_nbaiot,
    load_nbaiot,
    write_inventory_manifest,
)


def _write_csv(path, device_id, rows=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("device_id", "f0", "f1"))
        writer.writeheader()
        for row in range(rows):
            writer.writerow({"device_id": device_id, "f0": row, "f1": row + 1})


def test_missing_and_empty_raw_roots_fail_clearly(tmp_path):
    with pytest.raises(NbaiotDataError, match="missing"):
        discover_nbaiot(tmp_path / "missing")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(NbaiotDataError, match="empty"):
        discover_nbaiot(empty)


def test_inventory_and_loader_preserve_device_and_source(tmp_path):
    root = tmp_path / "nbaiot"
    _write_csv(root / "device-a" / "benign.csv", "device-a")
    _write_csv(root / "device-a" / "attack.csv", "device-a")
    inventory = discover_nbaiot(root)
    dataset = load_nbaiot(root)
    assert inventory.is_usable
    assert dataset.device_ids == ("device-a",)
    assert dataset.by_device("device-a", SampleSource.BENIGN).features.shape == (3, 2)
    assert "device-a" in inventory.to_json()
    manifest_path = tmp_path / "inventory.json"
    write_inventory_manifest(inventory, manifest_path)
    assert json.loads(manifest_path.read_text())["files"][0]["device_id"] == "device-a"


def test_unsupported_duplicate_and_mixed_identity_are_rejected(tmp_path):
    root = tmp_path / "nbaiot"
    _write_csv(root / "device-a" / "benign.csv", "device-a")
    _write_csv(root / "device-a" / "benign-copy.csv", "device-a")
    _write_csv(root / "device-a" / "attack.csv", "other-device")
    (root / "notes.txt").write_text("unsupported")
    inventory = discover_nbaiot(root)
    assert inventory.unsupported_files == ("notes.txt",)
    assert any("benign" in path for path in inventory.ambiguous_files)
    with pytest.raises(NbaiotDataError):
        load_nbaiot(root)
