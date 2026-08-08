"""Typed federated round-snapshot contracts."""

from dataclasses import dataclass

from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderState
from datp_core.domain.values.counts import RoundNumber
from datp_core.domain.values.ratios import MetricValue


@dataclass(frozen=True, slots=True)
class RoundSnapshot:
    round_number: RoundNumber
    state_dict: AutoencoderState
    mean_training_loss: MetricValue


@dataclass(frozen=True, slots=True)
class PersonalizedSnapshotSet:
    client: ClientIdentity
    snapshots: tuple[RoundSnapshot, ...]
