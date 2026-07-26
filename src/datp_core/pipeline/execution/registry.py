"""Immutable typed stage-handler registry."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.handlers import StageHandler


class DuplicateStageHandlerError(ValueError):
    """A handler is already registered for this stage."""


class MissingStageHandlerError(KeyError):
    """No handler is registered for the requested stage."""


class StageHandlerRegistry:
    def __init__(self, handlers: Mapping[StageKind, StageHandler]) -> None:
        seen: set[StageKind] = set()
        for kind in handlers:
            if kind in seen:
                raise DuplicateStageHandlerError(f"Duplicate handler registered for stage '{kind.value}'")
            seen.add(kind)
        self._handlers: Mapping[StageKind, StageHandler] = dict(handlers)

    def get(self, stage: StageKind) -> StageHandler:
        try:
            return self._handlers[stage]
        except KeyError:
            raise MissingStageHandlerError(f"No handler registered for stage '{stage.value}'") from None

    @property
    def registered_stages(self) -> tuple[StageKind, ...]:
        return tuple(sorted(self._handlers.keys(), key=lambda k: k.value))

    def __iter__(self) -> Iterator[StageKind]:
        return iter(self.registered_stages)

    def __contains__(self, stage: StageKind) -> bool:
        return stage in self._handlers

    def __len__(self) -> int:
        return len(self._handlers)
