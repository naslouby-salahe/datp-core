import struct
from datetime import UTC, datetime

from datp_core.data.edge_iiotset.chronology import validate_chronology


def _write_csv(path, clocks: tuple[str, ...]) -> None:
    path.write_text("frame.time\n" + "\n".join(clocks) + "\n", encoding="utf-8")


def _write_pcap(path, timestamps: tuple[datetime, ...]) -> None:
    with path.open("wb") as destination:
        destination.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 262_144, 1))
        for timestamp in timestamps:
            destination.write(struct.pack("<IIII", int(timestamp.timestamp()), timestamp.microsecond, 0, 0))


def test_paired_pcap_supplies_genuine_chronology(tmp_path) -> None:
    csv_path = tmp_path / "Distance.csv"
    pcap_path = tmp_path / "Distance.pcap"
    first = datetime(2021, 12, 27, 22, 58, 21, 314757, tzinfo=UTC)
    second = datetime(2021, 12, 27, 22, 58, 21, 314758, tzinfo=UTC)
    _write_csv(csv_path, ("2021 23:58:21.314757000", "2021 23:58:21.314758000"))
    _write_pcap(pcap_path, (first, second))

    chronology = validate_chronology("Distance", csv_path, pcap_path)

    assert chronology.validation.temporal_eligible is True
    assert chronology.validation.alignment_verified is True
    assert chronology.validation.evidence_row_count is not None
    assert chronology.validation.evidence_row_count.value == 2


def test_unmatched_pcap_is_not_chronology(tmp_path) -> None:
    csv_path = tmp_path / "Distance.csv"
    pcap_path = tmp_path / "Distance.pcap"
    timestamp = datetime(2021, 12, 27, 22, 58, 21, tzinfo=UTC)
    _write_csv(csv_path, ("2021 23:58:21.000000000", "2021 23:58:22.000000000"))
    _write_pcap(pcap_path, (timestamp, timestamp))

    chronology = validate_chronology("Distance", csv_path, pcap_path)

    assert chronology.validation.temporal_eligible is False
    assert chronology.validation.alignment_verified is False


def test_nonmonotonic_source_order_remains_temporal_eligible_after_alignment(tmp_path) -> None:
    """Complete alignment yields genuine capture times; source-order mono is diagnostic only.

    Journal Regime D-temporal stably sorts by capture time, so micro-inversions in CSV order
    do not revoke temporal eligibility when every row maps to a verified PCAP timestamp.
    """
    csv_path = tmp_path / "Distance.csv"
    pcap_path = tmp_path / "Distance.pcap"
    later = datetime(2021, 12, 27, 22, 58, 21, tzinfo=UTC)
    earlier = datetime(2021, 12, 27, 22, 58, 20, tzinfo=UTC)
    _write_csv(csv_path, ("2021 23:58:21.000000000", "2021 23:58:20.000000000"))
    _write_pcap(pcap_path, (later, earlier))

    chronology = validate_chronology("Distance", csv_path, pcap_path)

    assert chronology.validation.alignment_verified is True
    assert chronology.validation.is_monotonic is False
    assert chronology.validation.temporal_eligible is True
    assert "source-order inversion" in chronology.validation.reason


def test_missing_pcap_keeps_modbus_out_of_temporal_population(tmp_path) -> None:
    csv_path = tmp_path / "Modbus.csv"
    _write_csv(csv_path, ("192.168.0.128",))

    chronology = validate_chronology("Modbus", csv_path, tmp_path / "Modbus.pcap")

    assert chronology.validation.temporal_eligible is False
