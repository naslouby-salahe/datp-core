"""Typed federated round-snapshot contracts."""

from dataclasses import dataclass

from datp_core.core.numeric import MetricValue, RoundNumber
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderState


@dataclass(frozen=True, slots=True)
class RoundSnapshot:
    round_number: RoundNumber
    state_dict: AutoencoderState
    mean_training_loss: MetricValue


@dataclass(frozen=True, slots=True)
class PersonalizedSnapshotSet:
    client: ClientIdentity
    snapshots: tuple[RoundSnapshot, ...]
