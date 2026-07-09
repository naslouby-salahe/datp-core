"""Benign-training-fitted feature normalization for the anchor pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp_core.data.splits import ClientSplit, RegimeASplits, SplitSamples


class PreprocessingError(ValueError):
    """Raised when feature normalization would be undefined or leak evaluation data."""


@dataclass(frozen=True)
class FeatureScaler:
    mean: np.ndarray
    scale: np.ndarray

    def __post_init__(self) -> None:
        if self.mean.ndim != 1 or self.scale.ndim != 1 or self.mean.shape != self.scale.shape:
            raise PreprocessingError("feature scaler vectors must be one-dimensional and aligned")
        if np.any(self.scale <= 0.0):
            raise PreprocessingError("feature scaler values must be positive")
        self.mean.setflags(write=False)
        self.scale.setflags(write=False)

    def transform(self, samples: SplitSamples) -> SplitSamples:
        transformed = (samples.features - self.mean) / self.scale
        return SplitSamples(sample_ids=samples.sample_ids, features=transformed, source=samples.source)


def fit_feature_scaler(splits: RegimeASplits) -> FeatureScaler:
    train_rows = np.concatenate([client.train.features for client in splits.clients], axis=0)
    if not len(train_rows):
        raise PreprocessingError("cannot fit a scaler without benign training rows")
    mean = train_rows.mean(axis=0)
    scale = train_rows.std(axis=0)
    return FeatureScaler(mean=mean, scale=np.where(np.isclose(scale, 0.0), 1.0, scale))


def transform_regime_a_splits(splits: RegimeASplits, scaler: FeatureScaler) -> RegimeASplits:
    clients = tuple(
        ClientSplit(
            client_id=client.client_id,
            train=scaler.transform(client.train),
            calibration=scaler.transform(client.calibration),
            test_benign=scaler.transform(client.test_benign),
            test_attack=scaler.transform(client.test_attack),
            calibration_eligible=client.calibration_eligible,
        )
        for client in splits.clients
    )
    return RegimeASplits(
        seed=splits.seed,
        clients=clients,
        split_config_hash=splits.split_config_hash,
        split_type=splits.split_type,
    )
