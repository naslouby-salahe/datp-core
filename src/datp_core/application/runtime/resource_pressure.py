from dataclasses import dataclass

from datp_core.application.runtime.preflight import ResolvedBatchExecutionProfile
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.runtime.policies import PauseDecision, ResourcePressureSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class PressureResponse:
    action: PauseDecision
    frozen_batch_profile: ResolvedBatchExecutionProfile

    def __post_init__(self) -> None:
        if (
            type(self.action) is not PauseDecision
            or type(self.frozen_batch_profile) is not ResolvedBatchExecutionProfile
        ):
            raise DomainValidationError(
                detail="pressure responses must retain a typed action and the frozen batch profile",
                value=repr(self),
                constraint="PauseDecision and ResolvedBatchExecutionProfile",
            )


class CooperativePressureOrchestrator:
    def respond(
        self,
        *,
        snapshot: ResourcePressureSnapshot,
        frozen_batch_profile: ResolvedBatchExecutionProfile,
        proposed_batch_profile: ResolvedBatchExecutionProfile,
    ) -> PressureResponse:
        if proposed_batch_profile != frozen_batch_profile:
            raise DomainValidationError(
                detail="resource pressure cannot alter the frozen scientific batch profile",
                value=repr(proposed_batch_profile),
                constraint="exact resolved batch profile",
            )
        return PressureResponse(
            action=snapshot.recommended_action,
            frozen_batch_profile=frozen_batch_profile,
        )

    def resume(
        self,
        *,
        response: PressureResponse,
        frozen_batch_profile: ResolvedBatchExecutionProfile,
    ) -> ResolvedBatchExecutionProfile:
        if response.frozen_batch_profile != frozen_batch_profile:
            raise DomainValidationError(
                detail="pressure resume requires the identical preflight-frozen scientific batch profile",
                value=repr(response.frozen_batch_profile),
                constraint="exact resolved batch profile",
            )
        return frozen_batch_profile
