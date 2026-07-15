import re

from hypothesis import given
from hypothesis import strategies as st

from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash, sha256_bytes_content_hash

_HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


@given(st.binary(max_size=4096))
def test_content_hash_encoding_and_length_are_stable_for_arbitrary_bytes(content: bytes) -> None:
    blake3_digest = blake3_bytes_content_hash(content)
    sha256_digest = sha256_bytes_content_hash(content)

    assert _HEX_DIGEST.fullmatch(blake3_digest)
    assert _HEX_DIGEST.fullmatch(sha256_digest)
    assert len(blake3_digest) == 64
    assert len(sha256_digest) == 64
