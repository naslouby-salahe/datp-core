"""Single source of truth for federated reconstruction-error computation.

Every trainer (FedAvg, FedProx, Ditto global, Ditto personalized) reuses this module for
scoring; reconstruction-error semantics never live inside a trainer.
"""

import numpy as np
import torch

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import BatchSize, MetricValue
from datp_core.learning.autoencoder import FederatedAutoencoder
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE
from datp_core.runtime.compute import require_cuda_available

# Additive feature shift used only to verify reconstruction-error polarity (higher = more anomalous).
ANOMALY_POLARITY_FEATURE_PERTURBATION = MetricValue(5.0)
POLARITY_VERIFICATION_SAMPLE_LIMIT = 8


def reconstruction_errors(
    model: FederatedAutoencoder,
    features: np.ndarray,
    *,
    batch_size: BatchSize,
    device: torch.device,
) -> np.ndarray:
    """Mean per-row squared reconstruction error; higher means greater anomaly evidence."""
    require_cuda_available()
    if features.ndim != 2:
        raise ScientificContractError(
            "reconstruction scoring requires a 2-D feature matrix",
            subject=ContractSubject.FEATURES,
        )
    if features.shape[1] != model.input_width:
        raise ScientificContractError("feature width mismatch during scoring", subject=ContractSubject.FEATURES)
    if not np.isfinite(features).all():
        raise ScientificContractError("scoring features must be finite", subject=ContractSubject.FEATURES)
    model.eval()
    tensor = torch.as_tensor(np.array(features, dtype=np.float32), device=device)
    scores: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, tensor.shape[0], batch_size.value):
            batch = tensor[start : start + batch_size.value]
            reconstructed = model(batch)
            per_row = torch.mean((reconstructed - batch) ** 2, dim=1)
            scores.append(per_row.detach().cpu().numpy())
    if not scores:
        return np.asarray([], dtype=np.float64)
    return np.concatenate(scores).astype(np.float64, copy=False)


def assert_higher_score_is_anomaly_evidence(
    model: FederatedAutoencoder,
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
    limited = sample[: min(POLARITY_VERIFICATION_SAMPLE_LIMIT, sample.shape[0])]
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
