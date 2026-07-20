"""cattrs converter registration for domain dataclass structure and unstructure operations."""

from __future__ import annotations

from typing import Any

import cattrs

from ...domain.artifacts import ArtifactManifest
from ...domain.fingerprints import Checksum, Fingerprint
from ...domain.values import Probability, Seed

converter = cattrs.Converter()

# Hook for Fingerprint
converter.register_unstructure_hook(Fingerprint, lambda fp: fp.value)
converter.register_structure_hook(Fingerprint, lambda val, _: Fingerprint(value=str(val)))

# Hook for Checksum
converter.register_unstructure_hook(Checksum, lambda chk: chk.value)
converter.register_structure_hook(Checksum, lambda val, _: Checksum(value=str(val)))

# Hook for Seed
converter.register_unstructure_hook(Seed, lambda s: s.value)
converter.register_structure_hook(Seed, lambda val, _: Seed(value=int(val)))

# Hook for Probability
converter.register_unstructure_hook(Probability, lambda p: p.value)
converter.register_structure_hook(Probability, lambda val, _: Probability(value=float(val)))


def unstructure_manifest(manifest: ArtifactManifest) -> dict[str, Any]:
    return converter.unstructure(manifest)


def structure_manifest(data: dict[str, Any]) -> ArtifactManifest:
    return converter.structure(data, ArtifactManifest)
