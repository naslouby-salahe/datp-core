"""Shared miniature fixtures for scoring unit tests."""

from pathlib import Path

from tests.unit.learning.federated.helpers import AUTOENCODER, CHECKPOINT, fedavg_coordinate

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import CheckpointSelectionRule
from datp_core.core.numeric import Seed
from datp_core.detector.checkpoints.candidates import retain_checkpoint_candidates
from datp_core.detector.checkpoints.selection import select_checkpoint
from datp_core.detector.training.models import CheckpointCandidate
from datp_core.detector.training.models.snapshots import RoundSnapshot


def selected_checkpoint(output_directory: Path, seed: Seed | None = None) -> CheckpointCandidate:
    from datp_core.core.numeric import MetricValue
    from datp_core.detector.autoencoder import ReconstructionAutoencoder

    resolved_seed = Seed(0) if seed is None else seed
    coordinate = fedavg_coordinate(resolved_seed)
    model = ReconstructionAutoencoder(AUTOENCODER.widths)
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
