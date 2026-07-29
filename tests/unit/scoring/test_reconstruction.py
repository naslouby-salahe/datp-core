import numpy as np
import pytest
from tests.unit.learning.federated.helpers import AUTOENCODER

from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import BatchSize
from datp_core.learning.autoencoder import FederatedAutoencoder
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.reconstruction import assert_higher_score_is_anomaly_evidence, reconstruction_errors


def test_reconstruction_errors_returns_one_score_per_row() -> None:
    device = resolve_cuda_device()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    features = np.random.default_rng(0).normal(size=(8, 4)).astype(np.float32)
    scores = reconstruction_errors(model, features, batch_size=BatchSize(4), device=device)
    assert scores.shape == (8,)
    assert np.isfinite(scores).all()


def test_reconstruction_errors_rejects_wrong_feature_width() -> None:
    device = resolve_cuda_device()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    features = np.random.default_rng(0).normal(size=(8, 3)).astype(np.float32)
    with pytest.raises(ScientificContractError, match="width mismatch"):
        reconstruction_errors(model, features, batch_size=BatchSize(4), device=device)


def test_reconstruction_errors_rejects_non_finite_features() -> None:
    device = resolve_cuda_device()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    features = np.full((4, 4), np.inf, dtype=np.float32)
    with pytest.raises(ScientificContractError, match="finite"):
        reconstruction_errors(model, features, batch_size=BatchSize(4), device=device)


def test_reconstruction_errors_rejects_one_dimensional_input() -> None:
    device = resolve_cuda_device()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    features = np.zeros(4, dtype=np.float32)
    with pytest.raises(ScientificContractError, match="2-D"):
        reconstruction_errors(model, features, batch_size=BatchSize(4), device=device)


def test_assert_higher_score_is_anomaly_evidence_passes_for_a_fresh_model() -> None:
    device = resolve_cuda_device()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    sample = np.random.default_rng(0).normal(size=(4, 4)).astype(np.float32)
    assert_higher_score_is_anomaly_evidence(model, sample, batch_size=BatchSize(4), device=device)


def test_assert_higher_score_is_anomaly_evidence_rejects_empty_sample() -> None:
    device = resolve_cuda_device()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    empty_sample = np.zeros((0, 4), dtype=np.float32)
    with pytest.raises(ScientificContractError, match="cannot verify anomaly-score polarity"):
        assert_higher_score_is_anomaly_evidence(model, empty_sample, batch_size=BatchSize(4), device=device)
