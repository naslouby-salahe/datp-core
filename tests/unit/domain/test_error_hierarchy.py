from dataclasses import fields

from datp_core.domain import errors
from datp_core.domain.runtime.failure_dispositions import FailureDisposition

type ErrorExpectation = tuple[type[errors.DatpCoreError], FailureDisposition, tuple[str, ...]]


_ERROR_EXPECTATIONS: tuple[ErrorExpectation, ...] = (
    (errors.ConfigurationError, FailureDisposition.RUN_BLOCKING, ("section", "field", "mode")),
    (errors.DomainValidationError, FailureDisposition.RUN_BLOCKING, ("value", "constraint")),
    (errors.DatasetError, FailureDisposition.STAGE_BLOCKING, ("dataset", "regime", "coverage")),
    (errors.PartitionError, FailureDisposition.STAGE_BLOCKING, ("dataset", "regime", "coverage")),
    (errors.SplitError, FailureDisposition.STAGE_BLOCKING, ("dataset", "regime", "coverage")),
    (errors.PreprocessingError, FailureDisposition.STAGE_BLOCKING, ("strategy", "scope")),
    (errors.CudaUnavailableError, FailureDisposition.RUN_BLOCKING, ("required_stage",)),
    (errors.CudaDeviceMismatchError, FailureDisposition.RUN_BLOCKING, ("expected_device", "actual_device")),
    (errors.CudaOutOfMemoryError, FailureDisposition.STAGE_BLOCKING, ("batch", "vram")),
    (errors.RamPreflightError, FailureDisposition.RUN_BLOCKING, ("budget", "need")),
    (errors.ResourceBudgetExceededError, FailureDisposition.RUN_BLOCKING, ("budget", "estimate")),
    (
        errors.DiskSpaceError,
        FailureDisposition.RUN_BLOCKING,
        ("root", "projected_bytes", "reserve_bytes", "available_bytes"),
    ),
    (errors.UnsafeParallelismError, FailureDisposition.RUN_BLOCKING, ("requested_concurrency",)),
    (errors.InvalidCpuFallbackError, FailureDisposition.RUN_BLOCKING, ("stage", "policy")),
    (errors.TrainingError, FailureDisposition.STAGE_BLOCKING, ("seed", "round_number")),
    (errors.ClientFailureError, FailureDisposition.STAGE_BLOCKING, ("round_number", "client", "update_evidence")),
    (errors.ClientTimeoutError, FailureDisposition.STAGE_BLOCKING, ("round_number", "client", "update_evidence")),
    (
        errors.MalformedClientUpdateError,
        FailureDisposition.STAGE_BLOCKING,
        ("round_number", "client", "update_evidence"),
    ),
    (
        errors.NonFiniteClientUpdateError,
        FailureDisposition.STAGE_BLOCKING,
        ("round_number", "client", "update_evidence"),
    ),
    (
        errors.ClientShapeMismatchError,
        FailureDisposition.STAGE_BLOCKING,
        ("round_number", "client", "update_evidence"),
    ),
    (
        errors.FullParticipationViolationError,
        FailureDisposition.STAGE_BLOCKING,
        ("expected_roster", "completed_roster", "failed_roster"),
    ),
    (
        errors.RoundAbortedError,
        FailureDisposition.STAGE_BLOCKING,
        ("expected_roster", "completed_roster", "failed_roster"),
    ),
    (errors.CheckpointError, FailureDisposition.STAGE_BLOCKING, ("checkpoint_id", "content_hash")),
    (errors.CheckpointSelectionError, FailureDisposition.RUN_BLOCKING, ("candidate_evidence", "prohibited_input")),
    (errors.RecoveryStateMismatchError, FailureDisposition.STAGE_BLOCKING, ("training_identity", "round_number")),
    (errors.ResumeIncompatibilityError, FailureDisposition.STAGE_BLOCKING, ("training_identity", "round_number")),
    (errors.ScoringError, FailureDisposition.STAGE_BLOCKING, ("checkpoint_id", "split")),
    (errors.ThresholdError, FailureDisposition.STAGE_BLOCKING, ("policy", "missing_field")),
    (
        errors.AnchorReproductionFailure,
        FailureDisposition.STAGE_BLOCKING,
        ("reference_interval", "reproduced_interval"),
    ),
    (errors.EvaluationError, FailureDisposition.STAGE_BLOCKING, ("metric", "scope")),
    (errors.StatisticsError, FailureDisposition.STAGE_BLOCKING, ("method", "sample_size", "cause")),
    (errors.ArtifactError, FailureDisposition.STAGE_BLOCKING, ("artifact_id", "stage")),
    (errors.PartialArtifactError, FailureDisposition.STAGE_BLOCKING, ("artifact_id", "stage")),
    (errors.IncompleteArtifactBundleError, FailureDisposition.STAGE_BLOCKING, ("artifact_id", "stage")),
    (errors.ArtifactLockConflict, FailureDisposition.RETRYABLE_TRANSIENT, ("artifact_id", "owner")),
    (errors.PathResolutionError, FailureDisposition.RUN_BLOCKING, ("key", "root")),
    (errors.ProvenanceError, FailureDisposition.STAGE_BLOCKING, ("output_id", "missing_inputs")),
    (errors.StageFingerprintMismatchError, FailureDisposition.STAGE_BLOCKING, ("expected", "actual")),
    (errors.ReuseIncompatibilityError, FailureDisposition.STAGE_BLOCKING, ("reason",)),
    (errors.ReuseBlockedError, FailureDisposition.STAGE_BLOCKING, ("reason",)),
    (errors.DeterminismViolationError, FailureDisposition.RUN_BLOCKING, ("expected", "actual")),
    (errors.FeasibilityRejection, FailureDisposition.RUN_BLOCKING, ("reason",)),
    (errors.AmbiguousPlanError, FailureDisposition.RUN_BLOCKING, ("conflicting_cells",)),
    (errors.CyclicPlanError, FailureDisposition.RUN_BLOCKING, ("cycle",)),
    (errors.TestProfileValidationError, FailureDisposition.RUN_BLOCKING, ("profile", "violation")),
    (errors.EnvironmentIncompatibilityError, FailureDisposition.RUN_BLOCKING, ("required", "present")),
    (errors.ReportingError, FailureDisposition.STAGE_BLOCKING, ("output_id", "cause")),
)


def test_error_families_have_explicit_dispositions_and_typed_context() -> None:
    for error_type, disposition, context_fields in _ERROR_EXPECTATIONS:
        assert issubclass(error_type, errors.DatpCoreError)
        assert error_type.disposition is disposition
        assert tuple(field.name for field in fields(error_type)) == ("detail", *context_fields)


def test_cuda_oom_is_never_retryable() -> None:
    assert errors.CudaOutOfMemoryError.disposition is FailureDisposition.STAGE_BLOCKING
    assert errors.CudaOutOfMemoryError.disposition is not FailureDisposition.RETRYABLE_TRANSIENT


def test_error_uses_its_human_readable_detail_as_exception_text() -> None:
    error = errors.DomainValidationError(
        detail="threshold must be finite",
        value="nan",
        constraint="finite",
    )

    assert str(error) == "threshold must be finite"


def test_statistics_error_does_not_model_expected_degeneracy() -> None:
    assert not hasattr(errors, "StatisticalDegeneracyError")
