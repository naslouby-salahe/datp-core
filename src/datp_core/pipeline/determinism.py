"""The single canonical deterministic-seed-derivation formula, shared by every feature that derives
a seed from a namespace key and named components (dataloader shuffling in learning/, partition
retries in datasets/, calibration subsampling in thresholding/).

Consolidates three previously-independent but byte-identical reimplementations of this formula
(flagged in CURRENT_ARCHITECTURE.md as a reproducibility duplication risk): the strictest of the
three (requiring components sorted by name) is kept as the canonical contract.
"""

from __future__ import annotations

from hashlib import blake2b


def derive_seed(key: str, digest_bytes: int, components: tuple[tuple[str, int | str], ...]) -> int:
    """Derive a deterministic seed from an ordered key and named, ascending-sorted components."""
    if not key or digest_bytes < 1:
        raise ValueError("Seed derivation requires a key and positive digest length")
    if tuple(name for name, _ in components) != tuple(sorted(name for name, _ in components)):
        raise ValueError("Seed derivation components must be ordered by ascending name")
    encoded = "|".join((key, *(f"{name}={value}" for name, value in components))).encode("utf-8")
    return int.from_bytes(blake2b(encoded, digest_size=digest_bytes).digest(), "big") % (2**32)
