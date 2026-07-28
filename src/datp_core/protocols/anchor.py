"""Anchor declaration boundaries."""

from datp_core.domain.errors import UnresolvedScientificValueError


def require_anchor_tolerances() -> object:
    raise UnresolvedScientificValueError(
        "Metric-specific anchor tolerances are unresolved", subject="anchor tolerances"
    )
