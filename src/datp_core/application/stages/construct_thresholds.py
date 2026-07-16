from datp_core.application.ports.thresholding import (
    CentralizedThresholdConstructionResult,
    CentralizedThresholdConstructor,
    ConstructCentralizedThresholdRequest,
    ConstructThresholdsRequest,
    ThresholdConstructionResult,
    ThresholdConstructor,
)


def construct_thresholds(
    *,
    constructor: ThresholdConstructor,
    request: ConstructThresholdsRequest,
) -> ThresholdConstructionResult:
    return constructor.construct(request)


def construct_centralized_threshold(
    *,
    constructor: CentralizedThresholdConstructor,
    request: ConstructCentralizedThresholdRequest,
) -> CentralizedThresholdConstructionResult:
    return constructor.construct(request)
