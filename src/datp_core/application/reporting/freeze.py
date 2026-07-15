from dataclasses import dataclass

from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.feasibility import ScientificReadinessResult


@dataclass(frozen=True, slots=True, kw_only=True)
class ResultFreezeEligibility:
    result_freeze: ArtifactRef
    readiness: ScientificReadinessResult

    def __post_init__(self) -> None:
        if (
            type(self.result_freeze) is not ArtifactRef
            or self.result_freeze.artifact_type is not ArtifactType.RESULT_FREEZE
        ):
            raise DomainValidationError(
                detail="result freeze eligibility requires a typed result-freeze artefact",
                value=repr(self.result_freeze),
                constraint="ArtifactType.RESULT_FREEZE",
            )
        if type(self.readiness) is not ScientificReadinessResult:
            raise DomainValidationError(
                detail="result freeze eligibility requires typed scientific readiness",
                value=repr(self.readiness),
                constraint="ScientificReadinessResult",
            )

    @property
    def is_eligible(self) -> bool:
        return self.readiness.is_ready


class ResultFreezeEligibilityValidator:
    def validate(self, *, eligibility: ResultFreezeEligibility) -> None:
        if not eligibility.is_eligible:
            raise DomainValidationError(
                detail="result freeze is ineligible while scientific blockers remain",
                value=repr(eligibility.readiness.blockers),
                constraint="ScientificReadinessResult.is_ready",
            )
