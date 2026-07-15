from collections.abc import Sequence

from datp_core.domain.errors import ConfigurationError

OVERRIDE_PRECEDENCE = "ordered_override_wins"


def compose_configuration[Schema](base: Schema, overrides: Sequence[Schema]) -> Schema:
    resolved = base
    for override in overrides:
        if type(override) is not type(base):
            raise ConfigurationError(
                detail="configuration overrides must have the same declared schema as their base",
                section="compose",
                field="override",
                mode="compose",
            )
        resolved = override
    return resolved
