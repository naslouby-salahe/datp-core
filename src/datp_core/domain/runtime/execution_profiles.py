from dataclasses import dataclass

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.scores import B0ScoringBatchSpec, ScoringBatchSpec
from datp_core.domain.runtime.policies import StreamingChunkPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionProfileSpec:
    profile_id: str
    scoring_batch: ScoringBatchSpec
    b0_scoring_batch: B0ScoringBatchSpec
    streaming_chunk: StreamingChunkPolicy

    def __post_init__(self) -> None:
        if not _has_execution_profile_types(self):
            raise DomainValidationError(
                detail="execution profile requires an identifier and typed score and streaming policies",
                value=repr(self),
                constraint="non-empty profile identifier and exact execution policy component types",
            )
        if not _has_derived_b0_batching(self):
            raise DomainValidationError(
                detail="B0 batching must derive from the shared scoring batch policy",
                value=repr(self),
                constraint="B0 calibration and test batch sizes equal shared scoring batch sizes",
            )


def _has_execution_profile_types(profile: ExecutionProfileSpec) -> bool:
    return (
        bool(profile.profile_id)
        and type(profile.scoring_batch) is ScoringBatchSpec
        and type(profile.b0_scoring_batch) is B0ScoringBatchSpec
        and type(profile.streaming_chunk) is StreamingChunkPolicy
    )


def _has_derived_b0_batching(profile: ExecutionProfileSpec) -> bool:
    return (
        profile.b0_scoring_batch.calibration_batch_size == profile.scoring_batch.calibration_batch_size
        and profile.b0_scoring_batch.test_batch_size == profile.scoring_batch.test_batch_size
    )
