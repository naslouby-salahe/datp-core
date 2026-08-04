"""Reload and numerical equivalence validation for trusted estimator state."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.artifacts.serialization import TrustedScaler, load_estimator, transforms_are_equivalent
from datp_core.domain.enums import ContractSubject, TrustedEstimatorClassName
from datp_core.domain.errors import ArtifactIntegrityError, SerializationSafetyError
from datp_core.domain.values import AbsoluteTolerance


@dataclass(frozen=True, slots=True, eq=False)
class TransformReloadCheck:
    """Identity-based request containing mutable NumPy buffers for one reload check."""

    state_path: Path
    class_name: TrustedEstimatorClassName
    absolute_tolerance: AbsoluteTolerance
    source_matrix: np.ndarray
    expected_transformed: np.ndarray


def reload_and_compare_transform(check: TransformReloadCheck) -> TrustedScaler:
    if check.state_path.name != ProcessedAssetName.STATE.value:
        raise ArtifactIntegrityError(
            "fitted state path must use the skops state asset name",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    estimator = load_estimator(check.state_path, check.class_name)
    reloaded = np.asarray(estimator.transform(check.source_matrix), dtype=float)
    if not transforms_are_equivalent(
        check.expected_transformed,
        reloaded,
        check.absolute_tolerance,
    ):
        raise ArtifactIntegrityError(
            "transform-after-reload is not numerically equivalent to transform-before-save",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return estimator


def reject_untrusted_state(state_path: Path, class_name: TrustedEstimatorClassName) -> None:
    try:
        load_estimator(state_path, class_name)
    except SerializationSafetyError:
        return
    raise SerializationSafetyError("expected untrusted estimator rejection", subject=ContractSubject.ARTIFACT_PATH)
