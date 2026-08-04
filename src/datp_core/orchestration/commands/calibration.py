"""Typed calibration command and stage outcome."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.calibration.models import CalibrationReplicateManifest, EligibilityDecision
from datp_core.domain.enums import StageOperationId
from datp_core.domain.values import CalibrationSize, SubsampleReplicateCount
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CalibrationEligibilityProtocol
from datp_core.scoring.models import ScoreArtifactManifest


@dataclass(frozen=True, slots=True)
class CalibrateRequest:
    score_manifest: ScoreArtifactManifest
    protocol: CalibrationEligibilityProtocol
    calibration_sizes: tuple[CalibrationSize, ...]
    replicate_count: SubsampleReplicateCount


@dataclass(frozen=True, slots=True)
class CalibrateStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CALIBRATE
    eligibility: tuple[EligibilityDecision, ...]
    eligible_clients: tuple[ClientIdentity, ...]
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]
