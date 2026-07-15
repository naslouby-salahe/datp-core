from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.errors import CudaOutOfMemoryError, DomainValidationError
from datp_core.domain.runtime.policies import RunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class StageLifecycle:
    status: RunStatus = RunStatus.PLANNED
    terminal_oom_failure: bool = False

    def transition(self, target: RunStatus) -> StageLifecycle:
        if not _is_allowed_transition(
            source=self.status,
            target=target,
            terminal_oom_failure=self.terminal_oom_failure,
        ):
            raise DomainValidationError(
                detail="stage lifecycle transition is not permitted",
                value=f"{self.status.value}->{target.value}",
                constraint="closed Architecture stage lifecycle",
            )
        return StageLifecycle(status=target, terminal_oom_failure=self.terminal_oom_failure)

    def recover_transient_failure(self) -> StageLifecycle:
        if self.status is not RunStatus.FAILED or self.terminal_oom_failure:
            raise DomainValidationError(
                detail="only a non-OOM failed stage can be recovered as a classified transient failure",
                value=self.status.value,
                constraint="non-OOM FAILED stage",
            )
        return StageLifecycle(status=RunStatus.RECOVERED, terminal_oom_failure=False)

    def fail(self, error: Exception) -> StageLifecycle:
        if isinstance(error, CudaOutOfMemoryError):
            if self.status is not RunStatus.RUNNING:
                return self.transition(RunStatus.FAILED)
            return StageLifecycle(status=RunStatus.FAILED, terminal_oom_failure=True)
        return self.transition(RunStatus.FAILED)


def _is_allowed_transition(*, source: RunStatus, target: RunStatus, terminal_oom_failure: bool) -> bool:
    if terminal_oom_failure and target is RunStatus.RECOVERED:
        return False
    return (source, target) in {
        (RunStatus.PLANNED, RunStatus.READY),
        (RunStatus.PLANNED, RunStatus.BLOCKED),
        (RunStatus.READY, RunStatus.REUSED),
        (RunStatus.READY, RunStatus.RUNNING),
        (RunStatus.READY, RunStatus.BLOCKED),
        (RunStatus.RUNNING, RunStatus.COMPLETED),
        (RunStatus.RUNNING, RunStatus.FAILED),
        (RunStatus.RUNNING, RunStatus.INTERRUPTED),
        (RunStatus.RUNNING, RunStatus.PAUSED),
        (RunStatus.REUSED, RunStatus.COMPLETED),
        (RunStatus.INTERRUPTED, RunStatus.RECOVERED),
        (RunStatus.PAUSED, RunStatus.RECOVERED),
        (RunStatus.RECOVERED, RunStatus.RUNNING),
    }
