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


class CampaignRole(StrEnum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"


class RecipeRegistration(StrEnum):
    REGISTERED = "registered"
    SUPPRESSED = "suppressed"


class ArtifactPresence(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"


class ArtifactKind(StrEnum):
    JSON = "json"
    CSV = "csv"
    FIGURE = "figure"
    REPORT = "report"


class ArtifactRole(StrEnum):
    RESULT_JSON = "result_json"
    TABLE = "table"
    FIGURE = "figure"
    PUBLICATION = "publication"
    ANALYSIS = "analysis"


class ArtifactRequirement(StrEnum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"


class ArtifactValidity(StrEnum):
    MISSING = "missing"
    EMPTY = "empty"
    MALFORMED = "malformed"
    STALE = "stale"
    VALID = "valid"


class EvidenceCompletion(StrEnum):
    NOT_STARTED = "not_started"
    INCOMPLETE = "incomplete"
    EXECUTION_COMPLETE = "execution_complete"
    ANALYSIS_COMPLETE = "analysis_complete"
    PASSED = "passed"
    INVALID = "invalid"


class ExperimentRunDisposition(StrEnum):
    ALREADY_PASSED = "already_passed"
    COMPLETED = "completed"


class DeliveryBundleDisposition(StrEnum):
    ALREADY_CURRENT = "already_current"
    GENERATED = "generated"


class OwnedPathKind(StrEnum):
    TREE = "tree"
    DIRECTORY_RETAINING = "directory_retaining"
