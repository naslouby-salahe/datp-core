"""Safe serialization of trusted preprocessing estimators."""

from pathlib import Path
from typing import Any, cast

import numpy as np
import skops.io as sio
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.core.errors import SerializationSafetyError
from datp_core.data.preprocessing.contracts import TrustedScaler
from datp_core.data.preprocessing.validation import validate_serialization_equivalence

_TRUSTED_TYPES = frozenset({StandardScaler, MinMaxScaler})
_SKOPS_IO: Any = cast(Any, sio)


def dump_scaler(estimator: TrustedScaler, destination: Path) -> Checksum:
    if type(estimator) not in _TRUSTED_TYPES:
        raise SerializationSafetyError(f"unsupported preprocessing estimator type: {type(estimator).__qualname__}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _SKOPS_IO.dump(estimator, destination)
    return checksum_file(destination)


def load_scaler(path: Path, *, expected_checksum: Checksum | None = None) -> TrustedScaler:
    if expected_checksum is not None and checksum_file(path) != expected_checksum:
        raise SerializationSafetyError("persisted preprocessing estimator checksum mismatch")
    untrusted = _SKOPS_IO.get_untrusted_types(file=path)
    if untrusted:
        raise SerializationSafetyError(
            "persisted preprocessing estimator contains undeclared types",
            reason=", ".join(sorted(untrusted)),
        )
    estimator = _SKOPS_IO.load(path, trusted=[])
    if not isinstance(estimator, (StandardScaler, MinMaxScaler)):
        raise SerializationSafetyError(
            f"reloaded preprocessing estimator type is unsupported: {type(estimator).__qualname__}"
        )
    return estimator


def round_trip_scaler(
    estimator: TrustedScaler,
    destination: Path,
    probe: np.ndarray,
) -> tuple[TrustedScaler, Checksum]:
    checksum = dump_scaler(estimator, destination)
    reloaded = load_scaler(destination, expected_checksum=checksum)
    validate_serialization_equivalence(estimator, reloaded, probe)
    return reloaded, checksum
