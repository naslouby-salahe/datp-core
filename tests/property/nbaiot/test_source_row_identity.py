from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from datp_core.infrastructure.data.nbaiot.source import NBaIoTChunkedSourceAdapter

_FEATURE_COLUMNS = "feature_a,feature_b,feature_c"


def _write_device(raw_root: Path, *, rows: int) -> None:
    lines = [_FEATURE_COLUMNS]
    lines.extend(f"{index}.0,{index * 2}.0,{index * 3}.0" for index in range(rows))
    content = "\n".join(lines) + "\n"
    path = raw_root / "DeviceOne" / "benign_traffic.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@given(rows=st.integers(min_value=1, max_value=50), first_block=st.integers(min_value=256, max_value=4096))
def test_source_row_identity_is_independent_of_csv_block_size(rows: int, first_block: int) -> None:
    with TemporaryDirectory() as raw_directory, TemporaryDirectory() as first_out, TemporaryDirectory() as second_out:
        raw_root = Path(raw_directory)
        _write_device(raw_root, rows=rows)

        first = NBaIoTChunkedSourceAdapter(
            raw_root=raw_root, output_root=Path(first_out), csv_block_bytes=first_block
        ).materialize_device("DeviceOne")
        second = NBaIoTChunkedSourceAdapter(
            raw_root=raw_root, output_root=Path(second_out), csv_block_bytes=1024 * 1024
        ).materialize_device("DeviceOne")

        assert first.row_count == rows
        assert first.row_count == second.row_count
        assert first.row_order_checksum == second.row_order_checksum
