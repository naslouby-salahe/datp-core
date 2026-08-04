"""Typed threshold-construction commands and stage outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum
from datp_core.protocols.models import CentralizedQuantileProtocol
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.common import ThresholdConstructionResult
from datp_core.thresholding.dispatch import ThresholdConstructionRequest


@dataclass(frozen=True, slots=True)
class ConstructCentralizedThresholdRequest:
    coordinate: CentralizedTrainingCoordinate
    calibration_scores: PooledScoreArtifact
    output_directory: Path
    protocol: CentralizedQuantileProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ConstructCentralizedThresholdResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD
    publication_status: PublicationStatus
    threshold: PooledThresholdResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_FEDERATED_THRESHOLDS
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None
