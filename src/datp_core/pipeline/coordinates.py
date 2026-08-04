"""Neutral coordinate contract shared by pipeline lifecycle services."""

from typing import Protocol, runtime_checkable

from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.values import Seed


@runtime_checkable
class PipelineCoordinate(Protocol):
    """Minimum identity needed to bind persisted pipeline artifacts."""

    population: PopulationId
    training_seed: Seed
    split_protocol: SplitProtocolId
