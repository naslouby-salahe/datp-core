"""Reload and equivalence validation for fitted preprocessing state."""

from pathlib import Path

import numpy as np

from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.artifacts.serialization import TrustedScaler, load_estimator, transforms_are_equivalent
from datp_core.domain.errors import ArtifactIntegrityError, SerializationSafetyError
from datp_core.preprocessing.models import PreprocessingProtocol


def reload_and_compare_transform(
    state_path: Path,
    protocol: PreprocessingProtocol,
    source_matrix: np.ndarray,
    expected_transformed: np.ndarray,
) -> TrustedScaler:
    if state_path.name != ProcessedAssetName.STATE.value:
        raise ArtifactIntegrityError("fitted state path must use the skops state asset name", subject=str(state_path))
    estimator = load_estimator(state_path, protocol)
    reloaded = np.asarray(estimator.transform(source_matrix), dtype=float)
    if not transforms_are_equivalent(
        expected_transformed,
        reloaded,
        protocol.numerical_equivalence_absolute_tolerance,
    ):
        raise ArtifactIntegrityError(
            "transform-after-reload is not numerically equivalent to transform-before-save",
            subject=str(state_path),
        )
    return estimator


def reject_untrusted_state(state_path: Path, protocol: PreprocessingProtocol) -> None:
    try:
        load_estimator(state_path, protocol)
    except SerializationSafetyError:
        return
    raise SerializationSafetyError("expected untrusted estimator rejection", subject=str(state_path))
