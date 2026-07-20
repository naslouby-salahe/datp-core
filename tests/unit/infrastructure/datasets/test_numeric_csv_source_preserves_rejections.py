"""Streaming raw-source numeric validation tests."""

from pathlib import Path

import pytest

from datp_core.infrastructure.datasets.csv_source import read_numeric_csv_source


def test_numeric_csv_reader_preserves_valid_rows_and_explicit_rejections(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("a,b\n1.0,2.0\n,3.0\n4.0,not-a-number\n5.0,inf\n")
    result = read_numeric_csv_source(source, ("a", "b"))
    assert [row.values for row in result.rows] == [(1.0, 2.0)]
    assert [failure.source_row_index for failure in result.failures] == [2, 3, 4]


def test_numeric_csv_reader_rejects_missing_configured_header(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("a\n1.0\n")
    with pytest.raises(ValueError, match="missing required headers"):
        read_numeric_csv_source(source, ("a", "b"))
