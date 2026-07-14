"""Golden-snapshot scope: manifest, provenance, and B4 assignment/adjusted-Rand shapes only.

A snapshot here fixes the *shape* of a serialized structure so a silent field rename,
type change, or dropped field is caught. A snapshot must never fix a raw scientific
value (a score, a threshold, a metric, a p-value) as identity — that value belongs
inside a versioned artifact, not a test fixture.
"""

__all__: list[str] = []
