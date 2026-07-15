from datp_core.application.ports.thresholding import (
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
