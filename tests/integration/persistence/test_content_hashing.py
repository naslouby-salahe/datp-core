from pathlib import Path

from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash, blake3_file_content_hash


def test_large_synthetic_array_file_has_the_same_whole_and_mid_value_chunked_hash(tmp_path: Path) -> None:
    values = tuple(index.to_bytes(2, byteorder="little") for index in range(4096))
    content = b"".join(values) * 129
    artifact = tmp_path / "synthetic-array.bin"
    artifact.write_bytes(content)

    assert len(content) > 1024 * 1024
    assert blake3_file_content_hash(artifact, chunk_size=257) == blake3_bytes_content_hash(content)
