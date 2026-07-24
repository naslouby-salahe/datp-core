"""CICIoT2023 merged-source identity and label tests."""

from pathlib import Path

import pytest

from datp_core.data.adapters.ciciot2023 import (
    materialize_ciciot2023_merged_identity,
    materialize_ciciot2023_merged_source_row,
)
from datp_core.data.sources import LabeledSourceRow, SourceRow


def test_merged_file_defines_pseudo_client_and_benign_label(tmp_path: Path) -> None:
    root = tmp_path / "MERGED_CSV"
    source = root / "MergedTraffic.csv"
    identity = materialize_ciciot2023_merged_identity(source, 1, root, "BENIGN", "BENIGN")
    assert identity.client_id == "MergedTraffic.csv"
    assert not identity.is_attack


def test_merged_identity_rejects_blank_labels_and_paths_outside_the_configured_root(tmp_path: Path) -> None:
    root = tmp_path / "MERGED_CSV"
    with pytest.raises(ValueError, match="cannot be blank"):
        materialize_ciciot2023_merged_identity(root / "Merged.csv", 1, root, " ", "BENIGN")
    with pytest.raises(ValueError, match="escapes"):
        materialize_ciciot2023_merged_identity(tmp_path / "other.csv", 1, root, "BENIGN", "BENIGN")


def test_labeled_merged_source_row_preserves_numeric_and_label_provenance(tmp_path: Path) -> None:
    root = tmp_path / "MERGED_CSV"
    source_row = LabeledSourceRow(
        source_row=SourceRow(source_path=root / "MergedTraffic.csv", source_row_index=8, values=(1.0, 2.0)),
        label="DDoS",
    )
    materialized = materialize_ciciot2023_merged_source_row(source_row, root, "BENIGN")
    assert materialized.identity.client_id == "MergedTraffic.csv"
    assert materialized.identity.is_attack
    assert materialized.source_row.values == (1.0, 2.0)
