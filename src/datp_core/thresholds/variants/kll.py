from dataclasses import dataclass
from time import perf_counter
from typing import ClassVar, Protocol, cast

import datasketches  # type: ignore[import-untyped]
import numpy as np

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ContractSubject, FederatedThresholdMethod
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ByteCount,
    ElapsedSeconds,
    KllSketchSize,
    Quantile,
    Ratio,
    RelativeThresholdError,
    ReplicateIndex,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import ThresholdAssignment
from datp_core.thresholds.protocols import FederatedKllProtocol
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, exact_empirical_quantile


class _KllDoublesSketch(Protocol):
    def update(self, array: np.ndarray) -> None: ...

    def serialize(self) -> bytes: ...

    def merge(self, sketch: "_KllDoublesSketch") -> None: ...

    def get_quantile(self, rank: float) -> float: ...

    def normalized_rank_error(self, as_pmf: bool) -> float: ...


def _new_kll_sketch(sketch_size: KllSketchSize) -> _KllDoublesSketch:
    return cast(_KllDoublesSketch, datasketches.kll_doubles_sketch(sketch_size.value))


def _deserialize_kll_sketch(payload: bytes) -> _KllDoublesSketch:
    return cast(_KllDoublesSketch, datasketches.kll_doubles_sketch.deserialize(payload))


@dataclass(frozen=True, slots=True)
class SerializedKllSketch:
    client: ClientIdentity
    payload_hex: str
    byte_count: ByteCount
    build_serialization_elapsed: ElapsedSeconds


@dataclass(frozen=True, slots=True)
class KllReconstruction:
    replicate_index: ReplicateIndex
    client_sketches: tuple[SerializedKllSketch, ...]
    threshold: ThresholdValue
    normalized_rank_error: Ratio
    empirical_rank_error: Ratio
    absolute_threshold_error: AbsoluteThresholdError
    relative_threshold_error: RelativeThresholdError | None
    uploaded_bytes: ByteCount
    server_deserialize_merge_query_elapsed: ElapsedSeconds


@dataclass(frozen=True, slots=True)
class FederatedKllSharedThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    sketch_size: KllSketchSize
    threshold: ThresholdValue
    normalized_rank_error: Ratio
    assignments: tuple[ThresholdAssignment, ...]
    uploaded_bytes: ByteCount
    reconstructions: tuple[KllReconstruction, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD


def construct_federated_kll_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: FederatedKllProtocol,
    quantile: Quantile,
    sketch_size: KllSketchSize | None = None,
) -> FederatedKllSharedThresholdResult:
    if not eligible:
        raise ScientificContractError(
            ErrorMessage("KLL requires eligible benign calibration scores"), subject=ContractSubject.THRESHOLD
        )
    selected_k = sketch_size or protocol.primary_k
    if selected_k not in protocol.sensitivity_k:
        raise ScientificContractError(
            ErrorMessage("KLL sketch size must be one of the locked sensitivity values"),
            subject=ContractSubject.THRESHOLD,
        )
    ordered = tuple(sorted(eligible, key=lambda item: item.client))
    pooled = np.concatenate(tuple(item.as_array for item in ordered))
    exact_threshold = exact_empirical_quantile(pooled, quantile)
    reconstructions = tuple(
        _construct_reconstruction(
            ordered=ordered,
            sketch_size=selected_k,
            quantile=quantile,
            exact_threshold=exact_threshold,
            replicate_index=ReplicateIndex(index),
        )
        for index in range(protocol.reconstruction_replicate_count.value)
    )
    primary = reconstructions[0]
    return FederatedKllSharedThresholdResult(
        coordinate=ordered[0].coordinate,
        quantile=quantile,
        sketch_size=selected_k,
        threshold=primary.threshold,
        normalized_rank_error=primary.normalized_rank_error,
        assignments=tuple(ThresholdAssignment(item.client, primary.threshold) for item in ordered),
        uploaded_bytes=primary.uploaded_bytes,
        reconstructions=reconstructions,
    )


def _construct_reconstruction(
    *,
    ordered: tuple[ClientBenignCalibrationScores, ...],
    sketch_size: KllSketchSize,
    quantile: Quantile,
    exact_threshold: ThresholdValue,
    replicate_index: ReplicateIndex,
) -> KllReconstruction:
    client_sketches: list[SerializedKllSketch] = []
    for scores in ordered:
        client_started = perf_counter()
        sketch = _new_kll_sketch(sketch_size)
        sketch.update(scores.as_array)
        payload = sketch.serialize()
        client_sketches.append(
            SerializedKllSketch(
                client=scores.client,
                payload_hex=payload.hex(),
                byte_count=ByteCount(len(payload)),
                build_serialization_elapsed=ElapsedSeconds(perf_counter() - client_started),
            )
        )
    server_started = perf_counter()
    merged = _new_kll_sketch(sketch_size)
    for serialized in client_sketches:
        merged.merge(_deserialize_kll_sketch(bytes.fromhex(serialized.payload_hex)))
    threshold = ThresholdValue(float(merged.get_quantile(quantile.value)))
    server_elapsed = ElapsedSeconds(perf_counter() - server_started)
    pooled = np.concatenate(tuple(item.as_array for item in ordered))
    empirical_cdf = float(np.count_nonzero(pooled <= threshold.value) / pooled.size)
    absolute_error = AbsoluteThresholdError(abs(threshold.value - exact_threshold.value))
    relative_error = (
        RelativeThresholdError(absolute_error.value / abs(exact_threshold.value))
        if exact_threshold.value != 0.0
        else None
    )
    return KllReconstruction(
        replicate_index=replicate_index,
        client_sketches=tuple(client_sketches),
        threshold=threshold,
        normalized_rank_error=Ratio(float(merged.normalized_rank_error(False))),
        empirical_rank_error=Ratio(abs(empirical_cdf - quantile.value)),
        absolute_threshold_error=absolute_error,
        relative_threshold_error=relative_error,
        uploaded_bytes=ByteCount(sum(item.byte_count.value for item in client_sketches)),
        server_deserialize_merge_query_elapsed=server_elapsed,
    )
