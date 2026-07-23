"""Streaming labeled numeric source validation tests."""

from pathlib import Path

from datp_core.datasets.common import (
    LabeledSourceRow,
    SourceRowFailure,
    iter_labeled_numeric_csv_source,
)


def test_labeled_numeric_source_preserves_valid_rows_and_explicit_rejections(tmp_path: Path) -> None:
    source = tmp_path / "Merged.csv"
    source.write_text("first,second,Label\n1,2,BENIGN\n3,4, \nnot-a-number,5,DDoS\n6,7,DDoS,unexpected\n")
    results = tuple(iter_labeled_numeric_csv_source(source, ("first", "second"), "Label"))
    assert isinstance(results[0], LabeledSourceRow)
    assert results[0].source_row.values == (1.0, 2.0)
    assert results[0].label == "BENIGN"
    assert all(isinstance(result, SourceRowFailure) for result in results[1:])
    assert [result.reason for result in results[1:] if isinstance(result, SourceRowFailure)] == [
        "blank categorical label 'Label'",
        "unparseable numeric feature 'first'",
        "field count differs from configured header",
    ]
