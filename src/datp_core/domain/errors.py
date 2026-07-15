from dataclasses import dataclass
from typing import ClassVar

from datp_core.domain.experiments.feasibility import (
    BlockingReason,
    RejectionReason,
    ReuseIncompatibilityReason,
)
from datp_core.domain.runtime.failure_dispositions import FailureDisposition


@dataclass(frozen=True, slots=True, kw_only=True)
class DatpCoreError(Exception):
    detail: str
    disposition: ClassVar[FailureDisposition]

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfigurationError(DatpCoreError):
    section: str
    field: str
    mode: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainValidationError(DatpCoreError):
    value: str
    constraint: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetError(DatpCoreError):
    dataset: str
    regime: str
    coverage: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class PartitionError(DatasetError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitError(DatasetError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class PreprocessingError(DatpCoreError):
    strategy: str
    scope: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class CudaUnavailableError(DatpCoreError):
    required_stage: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class CudaDeviceMismatchError(DatpCoreError):
    expected_device: str
    actual_device: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class CudaOutOfMemoryError(DatpCoreError):
    batch: str
    vram: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class RamPreflightError(DatpCoreError):
    budget: str
    need: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceBudgetExceededError(DatpCoreError):
    budget: str
    estimate: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class DiskSpaceError(DatpCoreError):
    root: str
    projected_bytes: int
    reserve_bytes: int
    available_bytes: int
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class UnsafeParallelismError(DatpCoreError):
    requested_concurrency: int
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class InvalidCpuFallbackError(DatpCoreError):
    stage: str
    policy: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingError(DatpCoreError):
    seed: int
    round_number: int
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientUpdateError(DatpCoreError):
    round_number: int
    client: str
    update_evidence: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientFailureError(ClientUpdateError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientTimeoutError(ClientUpdateError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class MalformedClientUpdateError(ClientUpdateError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class NonFiniteClientUpdateError(ClientUpdateError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientShapeMismatchError(ClientUpdateError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class FullParticipationViolationError(DatpCoreError):
    expected_roster: str
    completed_roster: str
    failed_roster: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class RoundAbortedError(FullParticipationViolationError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointError(DatpCoreError):
    checkpoint_id: str
    content_hash: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionError(DatpCoreError):
    candidate_evidence: str
    prohibited_input: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryStateMismatchError(DatpCoreError):
    training_identity: str
    round_number: int
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ResumeIncompatibilityError(RecoveryStateMismatchError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoringError(DatpCoreError):
    checkpoint_id: str
    split: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdError(DatpCoreError):
    policy: str
    missing_field: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorReproductionFailure(DatpCoreError):  # noqa: N818 - prescribed public error type
    reference_interval: str
    reproduced_interval: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationError(DatpCoreError):
    metric: str
    scope: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticsError(DatpCoreError):
    method: str
    sample_size: int
    cause: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactError(DatpCoreError):
    artifact_id: str
    stage: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class PartialArtifactError(ArtifactError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class IncompleteArtifactBundleError(ArtifactError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactLockConflict(DatpCoreError):  # noqa: N818 - prescribed public error type
    artifact_id: str
    owner: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RETRYABLE_TRANSIENT


@dataclass(frozen=True, slots=True, kw_only=True)
class PathResolutionError(DatpCoreError):
    key: str
    root: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ProvenanceError(DatpCoreError):
    output_id: str
    missing_inputs: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class StageFingerprintMismatchError(DatpCoreError):
    expected: str
    actual: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ReuseIncompatibilityError(DatpCoreError):
    reason: ReuseIncompatibilityReason
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ReuseBlockedError(DatpCoreError):
    reason: BlockingReason
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class DeterminismViolationError(DatpCoreError):
    expected: str
    actual: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class FeasibilityRejection(DatpCoreError):  # noqa: N818 - prescribed public error type
    reason: RejectionReason
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class AmbiguousPlanError(DatpCoreError):
    conflicting_cells: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class CyclicPlanError(DatpCoreError):
    cycle: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class TestProfileValidationError(DatpCoreError):
    profile: str
    violation: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class EnvironmentIncompatibilityError(DatpCoreError):
    required: str
    present: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.RUN_BLOCKING


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportingError(DatpCoreError):
    output_id: str
    cause: str
    disposition: ClassVar[FailureDisposition] = FailureDisposition.STAGE_BLOCKING
