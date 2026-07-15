from dataclasses import dataclass
from io import StringIO

import pytest
from rich.console import Console

from datp_core.cli.main import invoke_command
from datp_core.composition.root import (
    BoundaryExitCode,
    CompositionCommandFailure,
    CompositionCommandResult,
    CompositionCommandSuccess,
    RunCompositionCommandRequest,
    error_exit_code,
)
from datp_core.domain.errors import (
    AmbiguousPlanError,
    AnchorReproductionFailure,
    ArtifactError,
    ArtifactLockConflict,
    CheckpointError,
    ConfigurationError,
    CudaUnavailableError,
    DatasetError,
    DatpCoreError,
    DeterminismViolationError,
    DomainValidationError,
    EnvironmentIncompatibilityError,
    EvaluationError,
    FeasibilityRejection,
    FullParticipationViolationError,
    PathResolutionError,
    PreprocessingError,
    ProvenanceError,
    RamPreflightError,
    ReportingError,
    ReuseBlockedError,
    ScoringError,
    StatisticsError,
    ThresholdError,
    TrainingError,
)
from datp_core.domain.errors import (
    TestProfileValidationError as ProfileValidationError,
)
from datp_core.domain.experiments.feasibility import BlockingReason, RejectionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class SyntheticCompositionUseCase:
    result: CompositionCommandResult

    def execute_command(self, request: RunCompositionCommandRequest) -> CompositionCommandResult:
        return self.result


def _console() -> tuple[Console, StringIO]:
    output = StringIO()
    return Console(file=output, color_system=None), output


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (
            ConfigurationError(detail="configuration", section="configuration", field="profile", mode="run"),
            BoundaryExitCode.CONFIGURATION,
        ),
        (
            DomainValidationError(detail="domain", value="value", constraint="constraint"),
            BoundaryExitCode.DOMAIN_VALIDATION,
        ),
        (
            DatasetError(detail="dataset", dataset="dataset", regime="regime", coverage="coverage"),
            BoundaryExitCode.DATASET,
        ),
        (
            PreprocessingError(detail="preprocessing", strategy="strategy", scope="scope"),
            BoundaryExitCode.PREPROCESSING,
        ),
        (CudaUnavailableError(detail="cuda", required_stage="stage"), BoundaryExitCode.CUDA),
        (RamPreflightError(detail="resource", budget="budget", need="need"), BoundaryExitCode.RESOURCE),
        (TrainingError(detail="training", seed=1, round_number=1), BoundaryExitCode.TRAINING),
        (
            CheckpointError(detail="checkpoint", checkpoint_id="checkpoint", content_hash="hash"),
            BoundaryExitCode.CHECKPOINT,
        ),
        (ScoringError(detail="scoring", checkpoint_id="checkpoint", split="test"), BoundaryExitCode.SCORING),
        (ThresholdError(detail="threshold", policy="policy", missing_field="field"), BoundaryExitCode.THRESHOLD),
        (
            AnchorReproductionFailure(
                detail="anchor", reference_interval="reference", reproduced_interval="reproduced"
            ),
            BoundaryExitCode.ANCHOR_REPRODUCTION,
        ),
        (EvaluationError(detail="evaluation", metric="metric", scope="scope"), BoundaryExitCode.EVALUATION),
        (
            StatisticsError(detail="statistics", method="method", sample_size=1, cause="cause"),
            BoundaryExitCode.STATISTICS,
        ),
        (ArtifactError(detail="artifact", artifact_id="artifact", stage="stage"), BoundaryExitCode.ARTIFACT),
        (ArtifactLockConflict(detail="lock", artifact_id="artifact", owner="owner"), BoundaryExitCode.ARTIFACT_LOCK),
        (PathResolutionError(detail="path", key="key", root="root"), BoundaryExitCode.PATH_RESOLUTION),
        (
            ProvenanceError(detail="provenance", output_id="output", missing_inputs="inputs"),
            BoundaryExitCode.PROVENANCE,
        ),
        (ReuseBlockedError(detail="reuse", reason=BlockingReason.INVALID_LINEAGE), BoundaryExitCode.REUSE),
        (
            DeterminismViolationError(detail="determinism", expected="expected", actual="actual"),
            BoundaryExitCode.DETERMINISM,
        ),
        (
            FeasibilityRejection(detail="feasibility", reason=RejectionReason.B_B_NO_METADATA),
            BoundaryExitCode.FEASIBILITY,
        ),
        (AmbiguousPlanError(detail="plan", conflicting_cells="cells"), BoundaryExitCode.PLAN),
        (
            ProfileValidationError(detail="profile", profile="profile", violation="violation"),
            BoundaryExitCode.TEST_PROFILE,
        ),
        (
            EnvironmentIncompatibilityError(detail="environment", required="required", present="present"),
            BoundaryExitCode.ENVIRONMENT,
        ),
        (ReportingError(detail="reporting", output_id="output", cause="cause"), BoundaryExitCode.REPORTING),
        (
            FullParticipationViolationError(
                detail="participation", expected_roster="expected", completed_roster="completed", failed_roster="failed"
            ),
            BoundaryExitCode.TRAINING,
        ),
    ),
)
def test_each_typed_error_family_has_a_distinct_exit_code(error: DatpCoreError, expected: BoundaryExitCode) -> None:
    assert error_exit_code(error) is expected


def test_unknown_typed_error_is_rejected_instead_of_receiving_a_generic_exit_code() -> None:
    @dataclass(frozen=True, slots=True, kw_only=True)
    class UnknownError(DatpCoreError):
        pass

    error = UnknownError(detail="unknown")

    with pytest.raises(TypeError, match="no process exit code"):
        error_exit_code(error)


def test_synthetic_composition_use_case_renders_a_boundary_success_and_exits_successfully() -> None:
    console, output = _console()

    exit_code = invoke_command(
        arguments=("run",),
        use_case=SyntheticCompositionUseCase(result=CompositionCommandSuccess(message="synthetic result")),
        console=console,
    )

    assert exit_code is BoundaryExitCode.SUCCESS
    assert output.getvalue().strip() == "synthetic result"


def test_synthetic_composition_failure_is_rendered_and_preserves_its_exit_code() -> None:
    console, output = _console()

    exit_code = invoke_command(
        arguments=("run",),
        use_case=SyntheticCompositionUseCase(
            result=CompositionCommandFailure(
                error=ConfigurationError(
                    detail="synthetic configuration failure", section="synthetic", field="ports", mode="run"
                )
            )
        ),
        console=console,
    )

    assert exit_code is BoundaryExitCode.CONFIGURATION
    assert output.getvalue().strip() == "synthetic configuration failure"
