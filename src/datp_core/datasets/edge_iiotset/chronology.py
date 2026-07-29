"""PCAP-backed chronology evidence for Edge benign sensor groups."""

import csv
import re
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.datasets.materialization import canonical_provenance_arrow_field
from datp_core.datasets.models import CanonicalProvenanceColumn, ChronologyValidation
from datp_core.domain.enums import AvailabilityStatus

from .schema import EdgeArtifactSuffix, EdgeCanonicalColumn, source_relative_path

_CLOCK_PATTERN = re.compile(r"^\s*\d{4}\s+(?P<clock>\d{2}:\d{2}:\d{2})\.(?P<fraction>\d{1,9})\s*$")
_MICROSECONDS_PER_DAY = 86_400_000_000
_MICROSECONDS_PER_SECOND = 1_000_000
_NANOSECONDS_PER_MICROSECOND = 1_000
_NANOSECONDS_PER_SECOND = 1_000_000_000
_TIMELINE_BATCH_SIZE = 65_536
_TIMELINE_SCHEMA = pa.schema(
    (
        canonical_provenance_arrow_field(CanonicalProvenanceColumn.SOURCE_ROW_INDEX),
        pa.field(EdgeCanonicalColumn.CAPTURE_TIMESTAMP, pa.timestamp("ns", tz="UTC")),
    )
)


@dataclass(frozen=True, slots=True)
class PcapChronology:
    pcap_path: Path
    validation: ChronologyValidation


@dataclass(frozen=True, slots=True)
class _PcapRecord:
    timestamp_nanoseconds: int
    utc_clock_microseconds: int


class _PcapAligner:
    def __init__(self, csv_path: Path, pcap_path: Path, expected_offset_microseconds: int | None = None) -> None:
        self.csv_path = csv_path
        self.pcap_path = pcap_path
        self.expected_offset_microseconds = expected_offset_microseconds
        self.alignment_offset_microseconds: int | None = None
        self.total_rows = 0
        self.duplicate_timestamp_count = 0
        self.out_of_order_rows = 0
        self.skipped_evidence_rows = 0
        self.trailing_evidence_rows = 0

    def matches(self) -> Iterator[int]:
        clocks = _csv_capture_clocks(self.csv_path)
        records = _pcap_records(self.pcap_path)
        first_record = self._first_match(clocks, records)
        yield self._record_match(first_record, None)
        previous_timestamp = first_record.timestamp_nanoseconds
        yield from self._remaining_matches(clocks, records, previous_timestamp)
        self.trailing_evidence_rows = sum(1 for _ in records)

    def validation(self, group_identity: str) -> ChronologyValidation:
        if self.alignment_offset_microseconds is None:
            raise ValueError("verified chronology must retain its PCAP display offset")
        temporal_eligible = self.out_of_order_rows == 0
        reason = (
            "Every CSV row is an ordered PCAP subsequence match after its verified display offset."
            if temporal_eligible
            else "PCAP alignment is verified, but matched capture timestamps are not monotonic."
        )
        return ChronologyValidation(
            group_identity=group_identity,
            status=AvailabilityStatus.AVAILABLE,
            total_rows=self.total_rows,
            parseable_rows=self.total_rows,
            invalid_rows=0,
            duplicate_timestamp_count=self.duplicate_timestamp_count,
            is_monotonic=temporal_eligible,
            reason=reason,
            temporal_eligible=temporal_eligible,
            evidence_source_path=source_relative_path(self.pcap_path),
            evidence_row_count=self.total_rows + self.skipped_evidence_rows + self.trailing_evidence_rows,
            alignment_verified=True,
            alignment_offset_microseconds=self.alignment_offset_microseconds,
            skipped_evidence_rows=self.skipped_evidence_rows,
            trailing_evidence_rows=self.trailing_evidence_rows,
        )

    def _first_match(self, clocks: Iterator[int], records: Iterator[_PcapRecord]) -> _PcapRecord:
        first_clock = next(clocks, None)
        first_record = next(records, None)
        if first_clock is None or first_record is None:
            raise ValueError("CSV and paired PCAP must both contain records")
        self.alignment_offset_microseconds = (first_clock - first_record.utc_clock_microseconds) % _MICROSECONDS_PER_DAY
        if self.expected_offset_microseconds not in (None, self.alignment_offset_microseconds):
            raise ValueError("paired PCAP display offset changed after chronology validation")
        return first_record

    def _remaining_matches(
        self, clocks: Iterator[int], records: Iterator[_PcapRecord], previous_timestamp: int
    ) -> Iterator[int]:
        offset = self.alignment_offset_microseconds
        if offset is None:
            raise ValueError("PCAP alignment offset is unavailable")
        for clock in clocks:
            record = self._next_matching_record(clock, records, offset)
            yield self._record_match(record, previous_timestamp)
            previous_timestamp = record.timestamp_nanoseconds

    def _next_matching_record(self, clock: int, records: Iterator[_PcapRecord], offset: int) -> _PcapRecord:
        record = next(records, None)
        while record is not None and not _clock_matches(clock, record.utc_clock_microseconds, offset):
            self.skipped_evidence_rows += 1
            record = next(records, None)
        if record is None:
            raise ValueError("PCAP does not cover every CSV record")
        return record

    def _record_match(self, record: _PcapRecord, previous_timestamp: int | None) -> int:
        self.total_rows += 1
        if previous_timestamp == record.timestamp_nanoseconds:
            self.duplicate_timestamp_count += 1
        if previous_timestamp is not None and record.timestamp_nanoseconds < previous_timestamp:
            self.out_of_order_rows += 1
        return record.timestamp_nanoseconds


def paired_capture_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(EdgeArtifactSuffix.PCAP)


def validate_chronology(group_identity: str, csv_path: Path, pcap_path: Path) -> PcapChronology:
    if not pcap_path.is_file():
        return PcapChronology(pcap_path, _unavailable_validation(group_identity, csv_path, "Paired PCAP is missing."))
    try:
        aligner = _PcapAligner(csv_path, pcap_path)
        for _ in aligner.matches():
            pass
    except (OSError, ValueError, csv.Error, struct.error) as error:
        return PcapChronology(
            pcap_path,
            _unavailable_validation(group_identity, csv_path, f"PCAP alignment could not be verified: {error}"),
        )
    return PcapChronology(pcap_path, aligner.validation(group_identity))


def write_capture_timeline(csv_path: Path, pcap_path: Path, destination: Path, offset_microseconds: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    aligner = _PcapAligner(csv_path, pcap_path, offset_microseconds)
    with pq.ParquetWriter(destination, _TIMELINE_SCHEMA, compression="zstd") as writer:
        indexes: list[int] = []
        timestamps: list[int] = []
        for index, timestamp in enumerate(aligner.matches()):
            indexes.append(index)
            timestamps.append(timestamp)
            if len(indexes) == _TIMELINE_BATCH_SIZE:
                _write_timeline_batch(writer, indexes, timestamps)
                indexes.clear()
                timestamps.clear()
        if indexes:
            _write_timeline_batch(writer, indexes, timestamps)


def _unavailable_validation(group_identity: str, csv_path: Path, reason: str) -> ChronologyValidation:
    total_rows = _csv_row_count(csv_path)
    return ChronologyValidation(
        group_identity=group_identity,
        status=AvailabilityStatus.UNAVAILABLE,
        total_rows=total_rows,
        parseable_rows=0,
        invalid_rows=total_rows,
        duplicate_timestamp_count=0,
        is_monotonic=False,
        reason=reason,
        temporal_eligible=False,
    )


def _csv_capture_clocks(path: Path) -> Iterator[int]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = next(reader, None)
        if header is None:
            raise ValueError("Edge CSV is missing its header")
        try:
            timestamp_column = header.index("frame.time")
        except ValueError as error:
            raise ValueError("Edge CSV is missing frame.time") from error
        for row in reader:
            if len(row) <= timestamp_column:
                raise ValueError("Edge CSV record is missing frame.time")
            yield _capture_clock_microseconds(row[timestamp_column])


def _capture_clock_microseconds(value: str) -> int:
    match = _CLOCK_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("Edge CSV frame.time is not a capture-clock value")
    hours, minutes, seconds = (int(component) for component in match.group("clock").split(":"))
    if hours > 23 or minutes > 59 or seconds > 59:
        raise ValueError("Edge CSV capture clock is outside a valid day")
    microseconds = int(match.group("fraction")[:6].ljust(6, "0"))
    return ((hours * 3_600 + minutes * 60 + seconds) * _MICROSECONDS_PER_SECOND) + microseconds


def _clock_matches(csv_clock_microseconds: int, pcap_clock_microseconds: int, offset_microseconds: int) -> bool:
    return (pcap_clock_microseconds + offset_microseconds) % _MICROSECONDS_PER_DAY == csv_clock_microseconds


def _pcap_records(path: Path) -> Iterator[_PcapRecord]:
    with path.open("rb") as source:
        source_size = path.stat().st_size
        endian, nanosecond_resolution = _pcap_format(source.read(24))
        header = struct.Struct(f"{endian}IIII")
        while record := source.read(header.size):
            if len(record) != header.size:
                raise ValueError("PCAP packet header is truncated")
            seconds, fraction, included_length, _ = header.unpack(record)
            source.seek(included_length, 1)
            if source.tell() > source_size:
                raise ValueError("PCAP packet body is truncated")
            microseconds = fraction // _NANOSECONDS_PER_MICROSECOND if nanosecond_resolution else fraction
            yield _PcapRecord(
                timestamp_nanoseconds=seconds * _NANOSECONDS_PER_SECOND + microseconds * _NANOSECONDS_PER_MICROSECOND,
                utc_clock_microseconds=(seconds % 86_400) * _MICROSECONDS_PER_SECOND + microseconds,
            )


def _pcap_format(global_header: bytes) -> tuple[str, bool]:
    if len(global_header) != 24:
        raise ValueError("PCAP global header is truncated")
    match global_header[:4]:
        case b"\xd4\xc3\xb2\xa1":
            return "<", False
        case b"\xa1\xb2\xc3\xd4":
            return ">", False
        case b"\x4d\x3c\xb2\xa1":
            return "<", True
        case b"\xa1\xb2\x3c\x4d":
            return ">", True
        case _:
            raise ValueError("unsupported PCAP format")


def _write_timeline_batch(writer: pq.ParquetWriter, indexes: list[int], timestamps: list[int]) -> None:
    writer.write_table(
        pa.table(
            (
                pa.array(indexes, type=pa.uint64()),
                pa.array(timestamps, type=pa.timestamp("ns", tz="UTC")),
            ),
            schema=_TIMELINE_SCHEMA,
        )
    )


def _csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        next(reader, None)
        return sum(1 for _ in reader)
