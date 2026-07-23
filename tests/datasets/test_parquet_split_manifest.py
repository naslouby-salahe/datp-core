"""Parquet materializations yield validated discrete split manifests."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.datasets.common import encode_split_manifest, read_materialized_split_evidence


def test_extracts_manifest_from_materialized_parquet(tmp_path: Path) -> None:
    payload = tmp_path / "materialized.parquet"
    pq.write_table(
        pa.table(
            {
                "split": ["train", "calibration", "calibration", "test"],
                "client_id": ["c1", "c1", "c1", "c1"],
                "is_attack": [False, False, False, True],
                "source_path": ["source.csv"] * 4,
                "source_row_index": [1, 2, 3, 4],
            }
        ),
        payload,
    )

    evidence = read_materialized_split_evidence(str(payload), minimum_benign_calibration_count=2)
    manifest = evidence.manifest

    assert manifest.eligible_client_ids == ("c1",)
    assert manifest.split_counts == {"calibration": 2, "test": 1, "train": 1}
    assert evidence.schema_columns[0] == ("split", "string")
    encoded = encode_split_manifest(manifest)
    assert b'"eligible_client_ids":["c1"]' in encoded
