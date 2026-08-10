from pathlib import Path
from shutil import rmtree

from datp_core.app.campaign import preprocess_datasets
from datp_core.app.contracts import OverwriteMode, ProgrammeExecutionMode
from datp_core.app.layout import ANCHOR_DIAGNOSTICS_DIRECTORY, SMOKE_OUTPUT_ROOT
from datp_core.app.models import AnchorCommandResult, DetailText
from datp_core.app.planning import PlanReason
from datp_core.app.validation import require_experiment_declaration
from datp_core.core.errors import AnchorReproductionError
from datp_core.core.identifiers import DatasetId, ExperimentId, ExperimentReadiness
from datp_core.experiments.anchor.contracts import AnchorGateStatus
from datp_core.experiments.anchor.gate import load_anchor_gate_decision
from datp_core.experiments.anchor.run import (
    VerifyAnchorStageRequest,
    clear_independent_package,
    collect_independent_observations_from_evaluations,
    default_anchor_diagnostics_directory,
    independent_package_directory,
    publish_independent_observations,
    verify_anchor,
)
from datp_core.experiments.anchor.spec import ANCHOR_DECISION_PROTOCOL, HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.models import ProgressHook
from datp_core.runtime.configuration import OUTPUTS_ROOT


def _output_root(mode: ProgrammeExecutionMode) -> Path:
    return SMOKE_OUTPUT_ROOT if mode is ProgrammeExecutionMode.SMOKE else OUTPUTS_ROOT


def reproduce_anchor(
    *,
    overwrite: OverwriteMode,
    mode: ProgrammeExecutionMode,
    progress: ProgressHook | None = None,
) -> AnchorCommandResult:
    preprocess_datasets(DatasetId.NBAIOT, overwrite=OverwriteMode.KEEP_EXISTING)
    output_root = _output_root(mode)
    diagnostics = default_anchor_diagnostics_directory(output_root)
    package_directory = independent_package_directory(output_root)
    if overwrite.requested:
        if diagnostics.exists():
            rmtree(diagnostics)
        clear_independent_package(package_directory)
    seed_cohort = (
        SeedCohort(values=(HISTORICAL_ANCHOR_SEED_COHORT.values[0],))
        if mode is ProgrammeExecutionMode.SMOKE
        else HISTORICAL_ANCHOR_SEED_COHORT
    )
    execute_declared_experiment_seed(
        declaration=require_experiment_declaration(ExperimentId.HISTORICAL_DATP_REPRODUCTION),
        seed_cohort=seed_cohort,
        reason=PlanReason("independent anchor reproduction supplies locked historical-seed execution prerequisites"),
        output_root=output_root,
        overwrite=overwrite.requested,
        progress=progress,
    )
    try:
        observations = collect_independent_observations_from_evaluations(
            output_root=output_root,
            seed_cohort=seed_cohort,
        )
        if observations:
            publish_independent_observations(package_directory, observations)
        result = verify_anchor(
            VerifyAnchorStageRequest(
                protocol=ANCHOR_DECISION_PROTOCOL,
                diagnostics_directory=diagnostics,
                independent_package_directory=package_directory,
                request_independent_reproduction=True,
            )
        )
    except AnchorReproductionError as error:
        return AnchorCommandResult(
            gate_status=AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            detail=DetailText(str(error)),
        )
    return AnchorCommandResult(
        gate_status=result.status.gate_status,
        dependent_readiness=result.status.dependent_readiness,
        detail=DetailText(
            f"seeds={seed_cohort.member_count.value} observations={result.status.observation_count.value} "
            f"mode={mode.value}"
        ),
    )


def verify_anchor_programme(*, mode: ProgrammeExecutionMode) -> AnchorCommandResult:
    output_root = _output_root(mode)
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=default_anchor_diagnostics_directory(output_root),
            independent_package_directory=independent_package_directory(output_root),
            request_independent_reproduction=True,
        )
    )
    return AnchorCommandResult(
        gate_status=result.status.gate_status,
        dependent_readiness=result.status.dependent_readiness,
        detail=DetailText(
            f"observations={result.status.observation_count.value} "
            f"discrepancies={result.status.discrepancy_count.value}"
        ),
    )


def anchor_status() -> AnchorCommandResult:
    try:
        decision = load_anchor_gate_decision(ANCHOR_DIAGNOSTICS_DIRECTORY)
    except AnchorReproductionError as error:
        return AnchorCommandResult(
            gate_status=AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            detail=DetailText(str(error)),
        )
    blocker = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    readiness = (
        "unblocked"
        if decision.status
        in {
            AnchorGateStatus.PASS,
            AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
        }
        else "blocked"
    )
    return AnchorCommandResult(
        gate_status=decision.status,
        dependent_readiness=decision.dependent_readiness,
        detail=DetailText(
            f"discrepancies={len(decision.reproduction.discrepancies)} blocker={blocker} dependents={readiness}"
        ),
    )
