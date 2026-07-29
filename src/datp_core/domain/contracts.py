"""Shared domain contracts."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Immutable, strict document model used at every serialized-domain boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
