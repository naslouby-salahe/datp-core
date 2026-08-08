"""Typed application-lifecycle contracts for DATP-Core programme execution."""

from enum import StrEnum


class ProgrammeExecutionMode(StrEnum):
    FULL = "full"
    SMOKE = "smoke"


class OverwriteMode(StrEnum):
    KEEP_EXISTING = "keep_existing"
    REBUILD = "rebuild"

    @property
    def requested(self) -> bool:
        return self is OverwriteMode.REBUILD


class AnchorRequirement(StrEnum):
    REQUIRED = "required"
    NOT_REQUIRED = "not_required"


class RecipeRegistration(StrEnum):
    REGISTERED = "registered"
    SUPPRESSED = "suppressed"


class ArtifactPresence(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
