"""Unit tests for canonical dataset materialization helpers."""

from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import DatasetId
from datp_core.core.numeric import ByteCount, RowCount
from datp_core.data.contracts import RawSourceFile, SourceFileRole
from datp_core.data.materialization import _inventory_checksum


def test_inventory_checksum_uses_domain_checksum_text() -> None:
    sources = (
        RawSourceFile(
            DatasetId.NBAIOT,
            Path("N-BaIoT/device_1/benign_traffic.csv"),
            ByteCount(128),
            Checksum("a" * 64),
            SourceFileRole.BENIGN,
            RowCount(10),
        ),
        RawSourceFile(
            DatasetId.NBAIOT,
            Path("N-BaIoT/device_1/gafgyt_attacks/combo.csv"),
            ByteCount(256),
            Checksum("b" * 64),
            SourceFileRole.ATTACK,
            None,
        ),
    )

    joined = "".join(
        "\t".join(
            (
                source.relative_path.as_posix(),
                str(source.size_bytes.value),
                source.checksum.value,
                source.role.value,
                "" if source.observed_row_count is None else str(source.observed_row_count),
            )
        )
        + "\n"
        for source in sources
    )

    assert _inventory_checksum(sources) == Checksum.from_text(joined)
