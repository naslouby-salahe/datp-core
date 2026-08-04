"""Benign-only calibration eligibility and subsampling stage."""

from dataclasses import dataclass

from datp_core.calibration.models import CalibrationReplicateManifest, EligibilityDecision
from datp_core.calibration.service import CalibrationRequest, calibrate
from datp_core.domain.values import CalibrationSize, SubsampleReplicateCount
from datp_core.pipeline.execution import PipelineStage
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CalibrationEligibilityProtocol
from datp_core.scoring.models import ScoreArtifactManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildCalibrationRequest:
    score_manifest: ScoreArtifactManifest
    protocol: CalibrationEligibilityProtocol
    calibration_sizes: tuple[CalibrationSize, ...]
    replicate_count: SubsampleReplicateCount


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildCalibrationResult:
    stage: PipelineStage
    eligibility: tuple[EligibilityDecision, ...]
    eligible_clients: tuple[ClientIdentity, ...]
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]


def build_calibration(request: BuildCalibrationRequest) -> BuildCalibrationResult:
    result = calibrate(
        CalibrationRequest(
            score_manifest=request.score_manifest,
            protocol=request.protocol,
            calibration_sizes=request.calibration_sizes,
            replicate_count=request.replicate_count,
        )
    )
    return BuildCalibrationResult(
        stage=PipelineStage.BUILD_CALIBRATION,
        eligibility=result.eligibility,
        eligible_clients=result.eligible_clients,
        replicate_manifests=result.replicate_manifests,
    )
