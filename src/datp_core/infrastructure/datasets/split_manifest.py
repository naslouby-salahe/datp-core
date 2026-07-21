"""Build immutable split-manifest domain records from materialized parquet evidence."""

from __future__ import annotations

import json

import pyarrow.parquet as pq

from datp_core.domain.splits import MaterializedSplitEvidence, SplitManifest, SplitManifestEntry, SplitMembership


def read_materialized_split_evidence(path: str, minimum_benign_calibration_count: int) -> MaterializedSplitEvidence:
    """Extract the materialized schema and validate its row-level split contract."""
    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    columns = ["split", "client_id", "is_attack", "source_path", "source_row_index"]
    if "chronology_key" in schema.names:
        columns.append("chronology_key")
    table = parquet.read(columns=columns)
    rows = table.to_pylist()
    manifest = SplitManifest(
        entries=tuple(
            SplitManifestEntry(
                source_path=str(row["source_path"]),
                source_row_index=int(row["source_row_index"]),
                client_id=str(row["client_id"]),
                membership=SplitMembership(str(row["split"])),
                is_attack=bool(row["is_attack"]),
                chronology_key=None if "chronology_key" not in row else int(row["chronology_key"]),
            )
            for row in rows
        ),
        minimum_benign_calibration_count=minimum_benign_calibration_count,
    )
    return MaterializedSplitEvidence(
        manifest=manifest,
        schema_columns=tuple((field.name, str(field.type)) for field in schema),
    )


def encode_split_manifest(manifest: SplitManifest) -> bytes:
    """Encode the complete row membership and derived evidence deterministically."""
    return json.dumps(
        {
            "schema_version": 1,
            "minimum_benign_calibration_count": manifest.minimum_benign_calibration_count,
            "entries": [
                {
                    "source_path": entry.source_path,
                    "source_row_index": entry.source_row_index,
                    "client_id": entry.client_id,
                    "membership": entry.membership.value,
                    "is_attack": entry.is_attack,
                    "chronology_key": entry.chronology_key,
                }
                for entry in manifest.entries
            ],
            "split_counts": manifest.split_counts,
            "class_counts": manifest.class_counts,
            "client_row_counts": manifest.client_row_counts,
            "eligible_client_ids": manifest.eligible_client_ids,
            "ineligible_client_ids": manifest.ineligible_client_ids,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
