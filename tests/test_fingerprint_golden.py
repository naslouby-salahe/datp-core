"""Golden snapshot characterization tests for BLAKE2 canonical fingerprinting."""

from datp_core.domain.fingerprints import Fingerprint, compute_fingerprint, compute_payload_checksum


def test_fingerprint_computation_stability() -> None:
    data = {"b": 2, "a": [1, 2, 3]}
    fp1 = compute_fingerprint(data)
    fp2 = compute_fingerprint({"a": [1, 2, 3], "b": 2})
    assert fp1 == fp2, "Fingerprint must be invariant to top-level key ordering"
    assert isinstance(fp1, Fingerprint)
    assert len(fp1.value) == 64, "BLAKE2b hex digest must be 64 characters long"


def test_payload_checksum_stability() -> None:
    payload = b"hello datp-core scientific reproducible pipeline"
    chk1 = compute_payload_checksum(payload)
    chk2 = compute_payload_checksum(payload)
    assert chk1 == chk2, "Payload checksum must be deterministic"
    assert len(chk1.value) == 64
