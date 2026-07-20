"""High-level Python API delegating to DatpApplication composition root."""

from __future__ import annotations

from datp_core.composition.root import DatpApplication, build_application


def get_application() -> DatpApplication:
    """Return initialized DatpApplication composition root."""
    return build_application()
