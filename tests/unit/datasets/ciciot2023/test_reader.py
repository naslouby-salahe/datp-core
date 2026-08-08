from datp_core.data.ciciot2023.reader import CICIoT2023Reader
from datp_core.data.ciciot2023.schema import (
    CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN,
    CICIOT2023_RAW_COLUMNS,
    CICIoT2023EligibilityReason,
)


def test_reader_retains_raw_label_and_provenance(tmp_path) -> None:
    path = tmp_path / "MERGED_CSV" / "Merged01.csv"
    path.parent.mkdir()
    path.write_text(",".join(CICIOT2023_RAW_COLUMNS) + "\n", encoding="utf-8")
    columns = CICIoT2023Reader().read(path).collect_schema().names()
    assert frozenset(("raw_label", "label", "source_path", "stable_row_id")).issubset(columns)


def test_reader_reports_unrecognized_label_and_rate_anomaly(tmp_path) -> None:
    path = tmp_path / "MERGED_CSV" / "Merged01.csv"
    path.parent.mkdir()
    path.write_text(
        ",".join(CICIOT2023_RAW_COLUMNS) + "\n" + ",".join(("1",) * 3 + ("inf",) + ("1",) * 35 + ("unknown",)),
        encoding="utf-8",
    )
    reader = CICIoT2023Reader()
    frame = reader.read(path)
    summary = reader.audit_summary(frame)

    expected = (summary.total_rows, summary.missing_or_unrecognized_labels, summary.infinite_rates, summary.empty_rates)
    assert tuple(item.value for item in expected) == (1, 1, 1, 0)


def test_model_input_eligibility_excludes_only_declared_anomalies(tmp_path) -> None:
    path = tmp_path / "MERGED_CSV" / "Merged01.csv"
    path.parent.mkdir()
    header = ",".join(CICIOT2023_RAW_COLUMNS)
    rows = (
        ",".join(("1",) * 39 + ("BENIGN",)),
        ",".join(("1",) * 3 + ("inf",) + ("1",) * 35 + ("BENIGN",)),
        ",".join(("1",) * 39 + ("unknown",)),
    )
    path.write_text(header + "\n" + "\n".join(rows), encoding="utf-8")

    reader = CICIoT2023Reader()
    frame = reader.read(path)
    audited = reader.model_input_eligibility_audit(frame).collect()

    summary = reader.audit_summary(frame)
    expected = (
        summary.total_rows,
        summary.missing_or_unrecognized_labels,
        summary.nonfinite_feature_rows,
        summary.eligible_rows,
    )
    assert tuple(item.value for item in expected) == (3, 1, 1, 1)

    assert audited[CICIoT2023EligibilityReason.NONFINITE_FEATURE].to_list() == [False, True, False]
    assert audited[CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL].to_list() == [False, False, True]

    eligible = audited.filter(audited[CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN])
    assert eligible.height == 1
    assert eligible[CICIoT2023EligibilityReason.NONFINITE_FEATURE].to_list() == [False]
    assert eligible[CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL].to_list() == [False]
