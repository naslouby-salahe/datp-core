"""Shared miniature fixtures for scoring unit tests."""

from pathlib import Path

from tests.unit.learning.federated.helpers import AUTOENCODER, CHECKPOINT, fedavg_coordinate

from datp_core.domain.enums import CheckpointSelectionRule
from datp_core.domain.values import Checksum, Seed
from datp_core.learning.federated.checkpointing import RoundSnapshot, retain_checkpoint_candidates, select_checkpoint
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.runtime.compute import resolve_cuda_device


def selected_checkpoint(output_directory: Path, seed: Seed | None = None) -> CheckpointCandidate:
    from datp_core.domain.values import MetricValue
    from datp_core.learning.autoencoder import ReconstructionAutoencoder

    resolved_seed = Seed(0) if seed is None else seed
    coordinate = fedavg_coordinate(resolved_seed)
    device = resolve_cuda_device()
    model = ReconstructionAutoencoder(AUTOENCODER.widths).to(device)
    state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
    snapshots = tuple(RoundSnapshot(candidate, state, MetricValue(0.1)) for candidate in CHECKPOINT.candidates)
    candidates = retain_checkpoint_candidates(
        coordinate,
        snapshots,
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=output_directory,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    decision = select_checkpoint(
        candidates,
        CHECKPOINT,
        coordinate=coordinate,
        client=None,
        selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
    )
    return decision.selected
