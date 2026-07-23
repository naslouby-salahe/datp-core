from pathlib import Path

from datp_core.configuration.fingerprints import compute_fingerprint
from datp_core.pipeline.fingerprints import (
    Fingerprint,
    compute_file_checksum,
    compute_payload_checksum,
)
from datp_core.pipeline.identifiers import DatasetId


def test_fingerprint_computation_is_stable_and_semantic() -> None:
    first = compute_fingerprint("scientific", {"b": 2, "a": [1, 2, 3]})
    second = compute_fingerprint("scientific", {"a": [1, 2, 3], "b": 2})
    assert first == second
    assert isinstance(first, Fingerprint)
    assert len(first.value) == 64
    assert first != compute_fingerprint("scientific", {"value": DatasetId("nbaiot")})


def test_payload_checksum_is_deterministic() -> None:
    payload = b"hello datp-core scientific reproducible pipeline"
    assert compute_payload_checksum(payload) == compute_payload_checksum(payload)


def test_file_checksum_matches_the_in_memory_checksum(tmp_path: Path) -> None:
    payload = b"chunked artifact checksum" * 1000
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)
    assert compute_file_checksum(path, chunk_size=13) == compute_payload_checksum(payload)
