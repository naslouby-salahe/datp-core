"""Stage: compose benign-only calibration eligibility and subsampling."""

from datp_core.calibration.service import CalibrationRequest, calibrate
from datp_core.orchestration.commands.calibration import (
    CalibrateRequest as _CalibrateRequest,
    CalibrateStageResult as _CalibrateStageResult,
)


def calibrate_stage(request: _CalibrateRequest) -> _CalibrateStageResult:
    result = calibrate(
        CalibrationRequest(
            score_manifest=request.score_manifest,
            protocol=request.protocol,
            calibration_sizes=request.calibration_sizes,
            replicate_count=request.replicate_count,
        )
    )
    return _CalibrateStageResult(
        eligibility=result.eligibility,
        eligible_clients=result.eligible_clients,
        replicate_manifests=result.replicate_manifests,
    )
