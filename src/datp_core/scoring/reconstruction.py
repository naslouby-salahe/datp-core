"""Federated polarity verification for reconstruction-error scores.

Reconstruction-error computation lives in learning.autoencoder; trainers and scorers
must reuse that single implementation rather than inventing alternate score semantics.
"""

import numpy as np
import torch

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import BatchSize
from datp_core.learning.autoencoder import ReconstructionAutoencoder, reconstruction_errors
from datp_core.protocols.anchor import (
    ANOMALY_POLARITY_FEATURE_PERTURBATION,
    FIXED_SCORE_ABSOLUTE_TOLERANCE,
    POLARITY_VERIFICATION_SAMPLE_LIMIT,
)


def assert_higher_score_is_anomaly_evidence(
    model: ReconstructionAutoencoder,
    sample: np.ndarray,
    *,
    batch_size: BatchSize,
    device: torch.device,
) -> None:
    """Verify MSE reconstruction error increases under larger feature perturbation."""
    if sample.shape[0] == 0:
        raise ScientificContractError(
            "cannot verify anomaly-score polarity without rows",
            subject=ContractSubject.SCORES,
        )
    limited = sample[: min(POLARITY_VERIFICATION_SAMPLE_LIMIT.value, sample.shape[0])]
    baseline = reconstruction_errors(model, limited, batch_size=batch_size, device=device)
    perturbed = reconstruction_errors(
        model,
        limited + ANOMALY_POLARITY_FEATURE_PERTURBATION.value,
        batch_size=batch_size,
        device=device,
    )
    if not np.all(perturbed >= baseline - FIXED_SCORE_ABSOLUTE_TOLERANCE.value):
        raise ScientificContractError(
            "reconstruction error polarity failed: higher error must indicate greater anomaly evidence",
            subject=ContractSubject.RECONSTRUCTION_ERROR,
        )
