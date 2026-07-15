from hashlib import sha256
from pathlib import Path

import pytest
from blake3 import blake3

from datp_core.infrastructure.persistence.hashing import (
    blake3_bytes_content_hash,
    blake3_chunks_content_hash,
    blake3_file_content_hash,
    sha256_bytes_content_hash,
    sha256_file_content_hash,
)


def test_blake3_byte_content_hash_is_repeatable_and_is_the_default_content_addressing_path() -> None:
    content = b"synthetic artifact contents"

    first = blake3_bytes_content_hash(content)

    assert first == blake3_bytes_content_hash(content)
    assert first == blake3(content).hexdigest()
    assert first != sha256(content).hexdigest()


def test_blake3_chunked_and_whole_file_hashes_agree(tmp_path: Path) -> None:
    content = b"synthetic-score-row\x00" * 31
    artifact = tmp_path / "scores.bin"
    artifact.write_bytes(content)

    assert blake3_chunks_content_hash((content[:17], content[17:])) == blake3_bytes_content_hash(content)
    assert blake3_file_content_hash(artifact, chunk_size=17) == blake3_bytes_content_hash(content)


def test_distinct_byte_strings_have_distinct_blake3_hashes() -> None:
    contents = (b"", b"a", b"b", b"a\x00", b"\x00a", b"synthetic parquet payload")

    assert len({blake3_bytes_content_hash(content) for content in contents}) == len(contents)


def test_sha256_is_only_used_through_an_explicitly_named_path(tmp_path: Path) -> None:
    content = b"cryptographic guarantee requested"
    artifact = tmp_path / "payload.bin"
    artifact.write_bytes(content)

    assert sha256_bytes_content_hash(content) == sha256(content).hexdigest()
    assert sha256_file_content_hash(artifact, chunk_size=11) == sha256(content).hexdigest()
    assert blake3_bytes_content_hash(content) == blake3(content).hexdigest()


def test_file_hashing_rejects_a_non_positive_chunk_size(tmp_path: Path) -> None:
    artifact = tmp_path / "payload.bin"
    artifact.write_bytes(b"synthetic")

    with pytest.raises(ValueError, match="chunk_size must be positive"):
        blake3_file_content_hash(artifact, chunk_size=0)
