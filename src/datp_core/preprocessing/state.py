"""Safe trusted preprocessing-estimator construction, persistence, and reload validation."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

import numpy as np
import skops.io as skops_io
from sklearn.base import BaseEstimator, clone
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ArtifactIntegrityError, SerializationSafetyError
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.domain.values.ratios import AbsoluteTolerance
from datp_core.preprocessing.contracts import ProcessedAssetName, TrustedEstimatorClassName

TrustedScaler = StandardScaler | MinMaxScaler
STANDARD_SCALER_WITH_MEAN = True
STANDARD_SCALER_WITH_STANDARD_DEVIATION = True
MIN_MAX_LOWER_BOUND = 0.0
MIN_MAX_UPPER_BOUND = 1.0
MIN_MAX_CLIP = False


class SerializationSubject(StrEnum):
    ESTIMATOR = "estimator"
    PREPROCESSING_ESTIMATOR = "preprocessing estimator"


@dataclass(frozen=True, slots=True)
class TrustedEstimatorDefinition:
    identity: TrustedEstimatorClassName
    estimator_type: type[TrustedScaler]
    constructor: Callable[[], TrustedScaler]


@dataclass(frozen=True, slots=True, eq=False)
class TransformReloadCheck:
    state_path: Path
    class_name: TrustedEstimatorClassName
    absolute_tolerance: AbsoluteTolerance
    source_matrix: np.ndarray
    expected_transformed: np.ndarray


_TRUSTED_ESTIMATORS: tuple[TrustedEstimatorDefinition, ...] = (
    TrustedEstimatorDefinition(
        identity=TrustedEstimatorClassName.STANDARD_SCALER,
        estimator_type=StandardScaler,
        constructor=lambda: StandardScaler(
            with_mean=STANDARD_SCALER_WITH_MEAN,
            with_std=STANDARD_SCALER_WITH_STANDARD_DEVIATION,
        ),
    ),
    TrustedEstimatorDefinition(
        identity=TrustedEstimatorClassName.MIN_MAX_SCALER,
        estimator_type=MinMaxScaler,
        constructor=lambda: MinMaxScaler(
            feature_range=(MIN_MAX_LOWER_BOUND, MIN_MAX_UPPER_BOUND),
            clip=MIN_MAX_CLIP,
        ),
    ),
)


def _definition_for(identity: TrustedEstimatorClassName) -> TrustedEstimatorDefinition:
    matches = tuple(definition for definition in _TRUSTED_ESTIMATORS if definition.identity is identity)
    if len(matches) != 1:
        raise SerializationSafetyError(
            "trusted estimator identity must resolve exactly once",
            subject=SerializationSubject.ESTIMATOR,
        )
    return matches[0]


def trusted_estimator_type_names() -> frozenset[str]:
    return frozenset(
        f"{definition.estimator_type.__module__}.{definition.estimator_type.__name__}"
        for definition in _TRUSTED_ESTIMATORS
    )


def resolve_trusted_estimator_type(class_name: TrustedEstimatorClassName) -> type[TrustedScaler]:
    return _definition_for(class_name).estimator_type


def construct_trusted_estimator(class_name: TrustedEstimatorClassName) -> TrustedScaler:
    return _definition_for(class_name).constructor()


def clone_trusted_scaler(estimator: TrustedScaler, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    if type(estimator) is not resolve_trusted_estimator_type(class_name):
        raise SerializationSafetyError(
            "estimator class does not match the trusted estimator identity",
            subject=SerializationSubject.ESTIMATOR,
        )
    return cast(TrustedScaler, clone(estimator))


def serialize_estimator(estimator: BaseEstimator | TrustedScaler, destination: Path) -> Checksum:
    estimator_type = type(estimator)
    trusted_types = tuple(definition.estimator_type for definition in _TRUSTED_ESTIMATORS)
    if estimator_type not in trusted_types:
        raise SerializationSafetyError(
            f"untrusted preprocessing estimator type {estimator_type.__module__}.{estimator_type.__name__}",
            subject=SerializationSubject.PREPROCESSING_ESTIMATOR,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(skops_io.dumps(estimator))
    return checksum_file(destination)


def load_estimator(path: Path, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    expected_type = resolve_trusted_estimator_type(class_name)
    loaded = skops_io.loads(path.read_bytes(), trusted=list(trusted_estimator_type_names()))
    if type(loaded) is not expected_type or not isinstance(loaded, (StandardScaler, MinMaxScaler)):
        raise SerializationSafetyError(
            "reloaded estimator class does not match the trusted estimator identity",
            subject=SerializationSubject.PREPROCESSING_ESTIMATOR,
        )
    return loaded


def transforms_are_equivalent(
    left: np.ndarray,
    right: np.ndarray,
    absolute_tolerance: AbsoluteTolerance,
) -> bool:
    if left.shape != right.shape:
        return False
    return bool(
        np.allclose(
            left,
            right,
            rtol=0.0,
            atol=absolute_tolerance.value,
            equal_nan=False,
        )
    )


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
