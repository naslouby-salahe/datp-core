"""CICIoT2023 merged-source identity and label extraction."""

from __future__ import annotations

from pathlib import Path

from datp_core.data.adapters.ciciot2023.models import CICIoT2023MaterializedRow, CICIoT2023RowIdentity
from datp_core.data.sources.models import LabeledSourceRow


def materialize_ciciot2023_merged_identity(
    source_path: Path,
    source_row_index: int,
    merged_root: Path,
    label: str,
    benign_label: str,
) -> CICIoT2023RowIdentity:
    try:
        source_path.relative_to(merged_root)
    except ValueError as exc:
        raise ValueError("CICIoT2023 merged source path escapes the configured merged root") from exc
    if source_row_index < 1:
        raise ValueError("CICIoT2023 source row index must be one-based and positive")
    normalized_label = label.strip()
    if not normalized_label:
        raise ValueError("CICIoT2023 merged source label cannot be blank")
    return CICIoT2023RowIdentity(
        client_id=source_path.name,
        is_attack=normalized_label.upper() != benign_label.upper(),
        source_path=source_path,
        source_row_index=source_row_index,
    )


def materialize_ciciot2023_merged_source_row(
    row: LabeledSourceRow, merged_root: Path, benign_label: str
) -> CICIoT2023MaterializedRow:
    return CICIoT2023MaterializedRow(
        identity=materialize_ciciot2023_merged_identity(
            source_path=row.source_row.source_path,
            source_row_index=row.source_row.source_row_index,
            merged_root=merged_root,
            label=row.label,
            benign_label=benign_label,
        ),
        multiclass_label=row.label,
        source_row=row.source_row,
    )
