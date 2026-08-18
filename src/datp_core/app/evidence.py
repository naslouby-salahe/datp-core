from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from pydantic import ValidationError

from datp_core.analysis.evidence import AnalysisAssetName, ExperimentMetricResults
from datp_core.analysis.mechanisms.support_interaction import SupportInteractionAnalysis
from datp_core.analysis.preparation import AnalysisDocument, ExternalAnalysisDocument, TemporalAnalysisDocument
from datp_core.app.contracts import (
    ArtifactKind,
    ArtifactRequirement,
    ArtifactRole,
    ArtifactValidity,
    EvidenceCompletion,
    OwnedPathKind,
)
from datp_core.app.layout import ResearchArtifact, ResearchDirectory
from datp_core.app.planning import PlanDisposition, expand_experiment_plan, seed_cohort_for
from datp_core.artifacts.integrity import artifact_byte_count, require_nonempty_file
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ExperimentId, PopulationId
from datp_core.detector.training.protocols import DITTO_REGULARIZATION_GRID, FEDPROX_COEFFICIENTS
from datp_core.experiments.centralized_reference import CIC_CENTRALIZED_REFERENCE
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.experiments.confirmatory.run import ConfirmatoryAssetDirectory
from datp_core.experiments.execution.evidence import load_evaluation_document
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory, ExecutionRootDirectory
from datp_core.experiments.external.run import (
    BoundedExternalAssetDirectory,
    ExternalBenignStatisticsAssetName,
    ExternalBenignStatisticsReport,
)
from datp_core.experiments.federated_threshold.run import (
    EstimationSummaryReport,
    FederatedEstimationArtifactName,
    FixedCoefficientSummaryReport,
)
from datp_core.experiments.heterogeneity.run import MechanismAnalysisDirectory
from datp_core.experiments.registry import require_experiment_declaration
from datp_core.experiments.temporal import TemporalArtifactDirectory
from datp_core.experiments.threshold_robustness.run import (
    CalibrationSizeAblationReport,
    ConformalCoverageReport,
    ContributorAvailabilityReport,
    EstimatorScopeSummaryReport,
    MethodCvSummaryReport,
    OnboardingCalibrationReport,
    PreprocessingGeometrySensitivityReport,
    QuantileSummaryReport,
    ShrinkageCurveReport,
    SizeAwareShrinkageReport,
    ThresholdRobustnessArtifactName,
)
from datp_core.presentation.export import (
    MECHANISM_REPORT_FILENAME,
    MECHANISM_RESULTS_FILENAME,
    PUBLICATION_FILENAME,
    PUBLICATION_SOURCE_DATA_FILENAME,
    MechanismPublicationDocument,
)
from datp_core.runtime.configuration import OUTPUTS_ROOT

JsonValidator = Callable[[Path], None]


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactSpec:
    role: ArtifactRole
    kind: ArtifactKind
    requirement: ArtifactRequirement
    parts: tuple[str, ...]
    json_validator: JsonValidator | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OwnedPath:
    parts: tuple[str, ...]
    kind: OwnedPathKind = OwnedPathKind.TREE
    retain_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentEvidenceContract:
    experiment: ExperimentId
    artifacts: tuple[ArtifactSpec, ...]
    owned_paths: tuple[OwnedPath, ...]
    executes: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactInspection:
    spec: ArtifactSpec
    path: Path
    validity: ArtifactValidity
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentEvidence:
    experiment: ExperimentId
    completion: EvidenceCompletion
    artifacts: tuple[ArtifactInspection, ...]
    output_root: Path

    @property
    def passed(self) -> bool:
        return self.completion is EvidenceCompletion.PASSED

    def paths_for(self, kind: ArtifactKind) -> tuple[Path, ...]:
        return tuple(
            item.path for item in self.artifacts if item.spec.kind is kind and item.validity is ArtifactValidity.VALID
        )


_FIGURE_BASED_MECHANISM_EXPERIMENTS = frozenset((ExperimentId.PER_CLIENT_SCORE_GEOMETRY,))


_CONFIRMATORY_CHILD_DIRECTORIES = (
    ConfirmatoryAssetDirectory.PHYSICAL_FAMILY_ADEQUACY.value,
    ConfirmatoryAssetDirectory.CALIBRATION_SUPPORT_BURDEN.value,
    ConfirmatoryAssetDirectory.NATURAL_DEVICE_CLIENT_IMPACT.value,
    ConfirmatoryAssetDirectory.MALWARE_FAMILY_SENSITIVITY.value,
    ConfirmatoryAssetDirectory.EQUITY_UTILITY_PARETO.value,
)


def evidence_contract(experiment_id: ExperimentId) -> ExperimentEvidenceContract:
    if experiment_id in {
        ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
        ExperimentId.OPTIONAL_EQUITY_INDICES,
    }:
        return _supplementary_for(experiment_id)
    builders: dict[ExperimentId, Callable[[], ExperimentEvidenceContract]] = {
        ExperimentId.SHARED_VS_LOCAL_CONFIRMATION: _confirmatory_contract,
        ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST: _fedprox_contract,
        ExperimentId.FEDAVG_LOCAL_FINE_TUNING: _fine_tuning_contract,
        ExperimentId.DITTO_ABSORPTION_STRESS_TEST: _ditto_contract,
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON: lambda: _estimation_contract(
            ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON, EstimationSummaryReport
        ),
        ExperimentId.FEDERATED_QUANTILE_ESTIMATION: lambda: _estimation_contract(
            ExperimentId.FEDERATED_QUANTILE_ESTIMATION, EstimationSummaryReport
        ),
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY: lambda: _estimation_contract(
            ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY, FixedCoefficientSummaryReport
        ),
        ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION: _edge_contract,
        ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY: _ciciot_contract,
        ExperimentId.EDGE_ONE_SHOT_RECALIBRATION: _temporal_contract,
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY: lambda: _robustness_contract(
            ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
            MethodCvSummaryReport,
            extra=(
                _artifact(
                    ArtifactRole.PUBLICATION,
                    ArtifactKind.REPORT,
                    _robustness_parts(
                        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
                        ThresholdRobustnessArtifactName.SHARED_CONSTRUCTION_PANEL.value,
                    ),
                ),
            ),
        ),
        ExperimentId.QUANTILE_SENSITIVITY: lambda: _robustness_contract(
            ExperimentId.QUANTILE_SENSITIVITY, QuantileSummaryReport
        ),
        ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY: lambda: _robustness_contract(
            ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY, EstimatorScopeSummaryReport
        ),
        ExperimentId.CALIBRATION_SIZE_ABLATION: lambda: _robustness_contract(
            ExperimentId.CALIBRATION_SIZE_ABLATION, CalibrationSizeAblationReport
        ),
        ExperimentId.CALIBRATION_COLD_START_ONBOARDING: lambda: _robustness_contract(
            ExperimentId.CALIBRATION_COLD_START_ONBOARDING, OnboardingCalibrationReport
        ),
        ExperimentId.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY: lambda: _robustness_contract(
            ExperimentId.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY, ContributorAvailabilityReport
        ),
        ExperimentId.FIXED_SHRINKAGE_CURVE: lambda: _robustness_contract(
            ExperimentId.FIXED_SHRINKAGE_CURVE, ShrinkageCurveReport
        ),
        ExperimentId.SIZE_AWARE_SHRINKAGE: lambda: _robustness_contract(
            ExperimentId.SIZE_AWARE_SHRINKAGE, SizeAwareShrinkageReport
        ),
        ExperimentId.LOCAL_CONFORMAL_COVERAGE: lambda: _robustness_contract(
            ExperimentId.LOCAL_CONFORMAL_COVERAGE, ConformalCoverageReport
        ),
        ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY: lambda: _robustness_contract(
            ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY, PreprocessingGeometrySensitivityReport
        ),
        ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP: lambda: _mechanism_contract(
            ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP, PopulationId.NBAIOT_DIRICHLET_CLIENTS, executes=True
        ),
        ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION: _support_interaction_contract,
        ExperimentId.PHYSICAL_FAMILY_ADEQUACY: lambda: _confirmatory_child_contract(
            ExperimentId.PHYSICAL_FAMILY_ADEQUACY, ConfirmatoryAssetDirectory.PHYSICAL_FAMILY_ADEQUACY
        ),
        ExperimentId.CALIBRATION_SUPPORT_BURDEN: lambda: _confirmatory_child_contract(
            ExperimentId.CALIBRATION_SUPPORT_BURDEN, ConfirmatoryAssetDirectory.CALIBRATION_SUPPORT_BURDEN
        ),
        ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT: lambda: _confirmatory_child_contract(
            ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT, ConfirmatoryAssetDirectory.NATURAL_DEVICE_CLIENT_IMPACT
        ),
        ExperimentId.MALWARE_FAMILY_SENSITIVITY: lambda: _confirmatory_child_contract(
            ExperimentId.MALWARE_FAMILY_SENSITIVITY, ConfirmatoryAssetDirectory.MALWARE_FAMILY_SENSITIVITY
        ),
        ExperimentId.EQUITY_UTILITY_PARETO: _equity_pareto_contract,
        ExperimentId.PER_CLIENT_SCORE_GEOMETRY: lambda: _mechanism_contract(
            ExperimentId.PER_CLIENT_SCORE_GEOMETRY, PopulationId.NBAIOT_NATURAL_DEVICES, executes=False
        ),
        ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION: lambda: _mechanism_contract(
            ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION, PopulationId.NBAIOT_NATURAL_DEVICES, executes=False
        ),
        ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF: lambda: _mechanism_contract(
            ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF, PopulationId.NBAIOT_NATURAL_DEVICES, executes=False
        ),
    }
    builder = builders.get(experiment_id)
    if builder is None:
        raise ScientificContractError(
            ErrorMessage(f"experiment has no evidence contract: {experiment_id.value}"),
            subject=experiment_id,
        )
    return builder()


def inspect_experiment_evidence(
    experiment_id: ExperimentId,
    *,
    output_root: Path = OUTPUTS_ROOT,
) -> ExperimentEvidence:
    contract = evidence_contract(experiment_id)
    artifacts = tuple(_inspect_artifact(spec, output_root) for spec in contract.artifacts)
    execution = _execution_state(contract, output_root)
    completion = _completion(artifacts, execution)
    return ExperimentEvidence(
        experiment=experiment_id,
        completion=completion,
        artifacts=artifacts,
        output_root=output_root,
    )


def require_experiment_passed(
    experiment_id: ExperimentId,
    *,
    output_root: Path = OUTPUTS_ROOT,
) -> ExperimentEvidence:
    evidence = inspect_experiment_evidence(experiment_id, output_root=output_root)
    if evidence.passed:
        return evidence
    raise ArtifactIntegrityError(
        ErrorMessage(
            f"experiment {experiment_id.value} is not complete: status={evidence.completion.value}; "
            f"{_failure_detail(evidence)}"
        ),
        subject=experiment_id,
    )


def purge_experiment_artifacts(
    experiment_id: ExperimentId,
    *,
    output_root: Path = OUTPUTS_ROOT,
) -> None:
    contract = evidence_contract(experiment_id)
    for owned in contract.owned_paths:
        path = output_root.joinpath(*owned.parts)
        if not _is_within(path, output_root):
            raise ScientificContractError(
                ErrorMessage(f"refusing to purge path outside the output root: {path}"),
                subject=experiment_id,
            )
        if owned.kind is OwnedPathKind.DIRECTORY_RETAINING:
            _purge_retaining(path, frozenset(owned.retain_names))
            continue
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            rmtree(path)


def _inspect_artifact(spec: ArtifactSpec, output_root: Path) -> ArtifactInspection:
    path = output_root.joinpath(*spec.parts)
    detail = "valid"
    validity = ArtifactValidity.VALID
    if not path.exists():
        validity, detail = ArtifactValidity.MISSING, "missing"
    elif path.is_dir():
        nonempty = any(child.is_file() and child.stat().st_size > 0 for child in path.rglob("*"))
        validity = ArtifactValidity.VALID if nonempty else ArtifactValidity.EMPTY
        detail = validity.value
    elif not path.is_file() or path.is_symlink():
        validity, detail = ArtifactValidity.MALFORMED, "not a regular file"
    else:
        try:
            if artifact_byte_count(path) == 0:
                validity, detail = ArtifactValidity.EMPTY, "empty"
            elif spec.json_validator is not None:
                spec.json_validator(path)
            else:
                require_nonempty_file(path)
        except (ArtifactIntegrityError, ScientificContractError, ValidationError, OSError, ValueError) as error:
            validity, detail = ArtifactValidity.MALFORMED, str(error)
    return ArtifactInspection(spec=spec, path=path, validity=validity, detail=detail)


def _completion(
    artifacts: tuple[ArtifactInspection, ...],
    execution: EvidenceCompletion,
) -> EvidenceCompletion:
    mandatory = tuple(item for item in artifacts if item.spec.requirement is ArtifactRequirement.MANDATORY)
    present = tuple(item for item in artifacts if item.validity is not ArtifactValidity.MISSING)
    malformed = tuple(
        item
        for item in present
        if item.validity in {ArtifactValidity.EMPTY, ArtifactValidity.MALFORMED, ArtifactValidity.STALE}
    )
    json_or_analysis = any(
        item.spec.role in {ArtifactRole.RESULT_JSON, ArtifactRole.ANALYSIS} and item.validity is ArtifactValidity.VALID
        for item in artifacts
    )
    if mandatory and all(item.validity is ArtifactValidity.VALID for item in mandatory):
        status = EvidenceCompletion.PASSED
    elif malformed:
        status = EvidenceCompletion.INVALID
    elif json_or_analysis:
        status = EvidenceCompletion.ANALYSIS_COMPLETE
    elif execution is EvidenceCompletion.EXECUTION_COMPLETE:
        status = EvidenceCompletion.EXECUTION_COMPLETE
    elif present or execution is EvidenceCompletion.INCOMPLETE:
        status = EvidenceCompletion.INCOMPLETE
    else:
        status = execution if execution is EvidenceCompletion.INVALID else EvidenceCompletion.NOT_STARTED
    return status


def _execution_state(contract: ExperimentEvidenceContract, output_root: Path) -> EvidenceCompletion:
    if not contract.executes:
        return EvidenceCompletion.EXECUTION_COMPLETE
    declaration = require_experiment_declaration(contract.experiment)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=seed_cohort_for(contract.experiment))
    executable = tuple(entry for entry in plan.entries if entry.disposition is PlanDisposition.EXECUTABLE)
    seen = 0
    invalid = False
    for entry in executable:
        path = (
            evaluation_run_directory(output_root, entry.coordinate)
            / EvaluationRunAssetDirectory.EVALUATION
            / FederatedEvaluationAssetName.DOCUMENT
        )
        if not path.is_file():
            continue
        seen += 1
        try:
            if artifact_byte_count(path) == 0:
                invalid = True
            else:
                load_evaluation_document(path)
        except (ScientificContractError, ArtifactIntegrityError, OSError, ValidationError):
            invalid = True
        if invalid:
            break
    if invalid:
        status = EvidenceCompletion.INVALID
    elif not executable or seen == 0:
        status = EvidenceCompletion.NOT_STARTED
    elif seen < len(executable):
        status = EvidenceCompletion.INCOMPLETE
    else:
        status = EvidenceCompletion.EXECUTION_COMPLETE
    return status


def _failure_detail(evidence: ExperimentEvidence) -> str:
    failures = tuple(
        f"{item.path.name}={item.validity.value}"
        for item in evidence.artifacts
        if item.spec.requirement is ArtifactRequirement.MANDATORY and item.validity is not ArtifactValidity.VALID
    )
    return ", ".join(failures) or evidence.completion.value


def _validate_model(model_type: type[StrictModel]) -> JsonValidator:
    def validate(path: Path) -> None:
        try:
            document = model_type.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValidationError, ValueError) as error:
            raise ArtifactIntegrityError(
                ErrorMessage(f"result JSON is missing, empty, or invalid: {path}"),
            ) from error
        if not _document_has_results(document):
            raise ArtifactIntegrityError(
                ErrorMessage(f"result JSON does not contain experiment results: {path}"),
            )

    return validate


def _document_has_results(document: StrictModel) -> bool:
    if isinstance(document, ExperimentMetricResults | SupportInteractionAnalysis):
        payload = document.observations
    elif isinstance(document, AnalysisDocument | ExternalAnalysisDocument):
        payload = document.contrasts.values
    elif isinstance(document, TemporalAnalysisDocument):
        payload = document.records
    elif isinstance(document, MechanismPublicationDocument):
        if document.mechanisms:
            return True
        return document.experiment in _FIGURE_BASED_MECHANISM_EXPERIMENTS
    else:
        payload = getattr(document, "rows", None)
        if not isinstance(payload, tuple):
            payload = getattr(document, "observations", None)
        if not isinstance(payload, tuple):
            payload = getattr(document, "mechanisms", None)
    return isinstance(payload, tuple) and payload != ()


def _artifact(
    role: ArtifactRole,
    kind: ArtifactKind,
    parts: tuple[str, ...],
    *,
    requirement: ArtifactRequirement = ArtifactRequirement.MANDATORY,
    json_validator: JsonValidator | None = None,
) -> ArtifactSpec:
    return ArtifactSpec(
        role=role,
        kind=kind,
        requirement=requirement,
        parts=parts,
        json_validator=json_validator,
    )


def _progress_log(experiment_id: ExperimentId) -> OwnedPath:
    return OwnedPath(parts=("logs", f"{experiment_id.value}.progress.log"))


def _evaluation_tree(experiment_id: ExperimentId) -> OwnedPath:
    return OwnedPath(parts=(experiment_id.value,))


def _confirmatory_analysis_parts(*tail: str) -> tuple[str, ...]:
    return (
        ConfirmatoryAssetDirectory.ROOT.value,
        PopulationId.NBAIOT_NATURAL_DEVICES.value,
        ConfirmatoryAssetDirectory.ANALYSIS.value,
        *tail,
    )


def _confirmatory_contract() -> ExperimentEvidenceContract:
    return ExperimentEvidenceContract(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                _confirmatory_analysis_parts(AnalysisAssetName.DOCUMENT.value),
                json_validator=_validate_model(AnalysisDocument),
            ),
            _artifact(
                ArtifactRole.TABLE,
                ArtifactKind.CSV,
                _confirmatory_analysis_parts(PUBLICATION_SOURCE_DATA_FILENAME),
            ),
            _artifact(
                ArtifactRole.PUBLICATION,
                ArtifactKind.REPORT,
                _confirmatory_analysis_parts(PUBLICATION_FILENAME),
            ),
        ),
        owned_paths=(
            _evaluation_tree(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION),
            _progress_log(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION),
            OwnedPath(
                parts=_confirmatory_analysis_parts(),
                kind=OwnedPathKind.DIRECTORY_RETAINING,
                retain_names=_CONFIRMATORY_CHILD_DIRECTORIES,
            ),
        ),
        executes=True,
    )


def _confirmatory_child_contract(
    experiment_id: ExperimentId,
    directory: ConfirmatoryAssetDirectory,
) -> ExperimentEvidenceContract:
    parts = _confirmatory_analysis_parts(directory.value)
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=_mechanism_artifacts(parts),
        owned_paths=(OwnedPath(parts=parts),),
        executes=False,
    )


def _equity_pareto_contract() -> ExperimentEvidenceContract:
    parts = _confirmatory_analysis_parts(ConfirmatoryAssetDirectory.EQUITY_UTILITY_PARETO.value)
    return ExperimentEvidenceContract(
        experiment=ExperimentId.EQUITY_UTILITY_PARETO,
        artifacts=(
            *_mechanism_artifacts(parts),
            _artifact(
                ArtifactRole.PUBLICATION,
                ArtifactKind.REPORT,
                (*parts, "calibration_target_attainment.md"),
            ),
        ),
        owned_paths=(OwnedPath(parts=parts),),
        executes=False,
    )


def _mechanism_artifacts(parts: tuple[str, ...]) -> tuple[ArtifactSpec, ...]:
    return (
        _artifact(
            ArtifactRole.RESULT_JSON,
            ArtifactKind.JSON,
            (*parts, MECHANISM_RESULTS_FILENAME),
            json_validator=_validate_model(MechanismPublicationDocument),
        ),
        _artifact(ArtifactRole.TABLE, ArtifactKind.CSV, (*parts, PUBLICATION_SOURCE_DATA_FILENAME)),
        _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, PUBLICATION_FILENAME)),
        _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, MECHANISM_REPORT_FILENAME)),
    )


def _mechanism_contract(
    experiment_id: ExperimentId,
    population: PopulationId,
    *,
    executes: bool,
) -> ExperimentEvidenceContract:
    parts = (
        MechanismAnalysisDirectory.ROOT.value,
        experiment_id.value,
        population.value,
        MechanismAnalysisDirectory.ANALYSIS.value,
    )
    owned = [OwnedPath(parts=parts)]
    if executes:
        owned.extend((_evaluation_tree(experiment_id), _progress_log(experiment_id)))
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=_mechanism_artifacts(parts),
        owned_paths=tuple(owned),
        executes=executes,
    )


def _support_interaction_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION
    parts = (
        MechanismAnalysisDirectory.ROOT.value,
        experiment_id.value,
        PopulationId.NBAIOT_DIRICHLET_CLIENTS.value,
        MechanismAnalysisDirectory.ANALYSIS.value,
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*parts, "support_interaction_analysis.json"),
                json_validator=_validate_model(SupportInteractionAnalysis),
            ),
            _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, "support_interaction_surface.md")),
        ),
        owned_paths=(
            OwnedPath(parts=parts),
            _evaluation_tree(experiment_id),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _supplementary_for(experiment_id: ExperimentId) -> ExperimentEvidenceContract:
    parts = (ResearchDirectory.SUPPLEMENTARY.value, experiment_id.value)
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*parts, ResearchArtifact.RESULTS.value),
                json_validator=_validate_model(ExperimentMetricResults),
            ),
            _artifact(ArtifactRole.TABLE, ArtifactKind.CSV, (*parts, ResearchArtifact.RESULTS_TABLE.value)),
            _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, ResearchArtifact.EVIDENCE_REPORT.value)),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=parts),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _robustness_parts(experiment_id: ExperimentId, *tail: str) -> tuple[str, ...]:
    return (
        ThresholdRobustnessArtifactName.ROOT.value,
        experiment_id.value,
        PopulationId.NBAIOT_NATURAL_DEVICES.value,
        ThresholdRobustnessArtifactName.ANALYSIS.value,
        *tail,
    )


def _robustness_contract(
    experiment_id: ExperimentId,
    model_type: type[StrictModel],
    *,
    extra: tuple[ArtifactSpec, ...] = (),
) -> ExperimentEvidenceContract:
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                _robustness_parts(experiment_id, ThresholdRobustnessArtifactName.SUMMARY.value),
                json_validator=_validate_model(model_type),
            ),
            _artifact(
                ArtifactRole.TABLE,
                ArtifactKind.CSV,
                _robustness_parts(experiment_id, ResearchArtifact.RESULTS_TABLE.value),
            ),
            *extra,
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=_robustness_parts(experiment_id)),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _estimation_contract(experiment_id: ExperimentId, model_type: type[StrictModel]) -> ExperimentEvidenceContract:
    parts = (
        FederatedEstimationArtifactName.ROOT.value,
        experiment_id.value,
        PopulationId.NBAIOT_NATURAL_DEVICES.value,
        FederatedEstimationArtifactName.ANALYSIS.value,
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*parts, FederatedEstimationArtifactName.SUMMARY.value),
                json_validator=_validate_model(model_type),
            ),
            _artifact(ArtifactRole.TABLE, ArtifactKind.CSV, (*parts, ResearchArtifact.RESULTS_TABLE.value)),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=parts),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _edge_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION
    analysis = (
        BoundedExternalAssetDirectory.ANALYSIS.value,
        experiment_id.value,
        PopulationId.EDGE_SENSOR_CLIENTS.value,
    )
    benign = (
        ExternalBenignStatisticsAssetName.ROOT.value,
        experiment_id.value,
        PopulationId.EDGE_SENSOR_CLIENTS.value,
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*analysis, AnalysisAssetName.EXTERNAL_DOCUMENT.value),
                json_validator=_validate_model(ExternalAnalysisDocument),
            ),
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*benign, ExternalBenignStatisticsAssetName.SUMMARY.value),
                json_validator=_validate_nonempty_json_object,
            ),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=(ExecutionRootDirectory.BOUNDED_EVIDENCE.value, experiment_id.value)),
            OwnedPath(parts=analysis),
            OwnedPath(parts=benign),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _ciciot_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY
    analysis = (
        BoundedExternalAssetDirectory.ANALYSIS.value,
        experiment_id.value,
        PopulationId.CICIOT_FILE_CLIENTS.value,
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*analysis, AnalysisAssetName.EXTERNAL_DOCUMENT.value),
                json_validator=_validate_model(ExternalAnalysisDocument),
            ),
            _artifact(
                ArtifactRole.PUBLICATION,
                ArtifactKind.REPORT,
                (
                    "centralized_reference",
                    CIC_CENTRALIZED_REFERENCE.dataset.value,
                    str(CONFIRMATORY_SEED_COHORT.values[0].value),
                    "report",
                ),
                requirement=ArtifactRequirement.OPTIONAL,
            ),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=(ExecutionRootDirectory.BOUNDED_EVIDENCE.value, experiment_id.value)),
            OwnedPath(parts=analysis),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _temporal_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.EDGE_ONE_SHOT_RECALIBRATION
    declaration = require_experiment_declaration(experiment_id)
    artifacts = tuple(
        _artifact(
            ArtifactRole.RESULT_JSON,
            ArtifactKind.JSON,
            (
                ExecutionRootDirectory.BOUNDED_EVIDENCE.value,
                experiment_id.value,
                declaration.population.value,
                declaration.role.value,
                TemporalArtifactDirectory.ANALYSIS.value,
                method.value,
                AnalysisAssetName.TEMPORAL_DOCUMENT.value,
            ),
            json_validator=_validate_model(TemporalAnalysisDocument),
        )
        for method in declaration.federated_thresholds
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=artifacts,
        owned_paths=(
            OwnedPath(parts=(ExecutionRootDirectory.BOUNDED_EVIDENCE.value, experiment_id.value)),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _fedprox_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST
    artifacts = tuple(
        _artifact(
            spec.role,
            spec.kind,
            (
                ExecutionRootDirectory.FEDPROX_STRESS_TEST.value,
                PopulationId.NBAIOT_NATURAL_DEVICES.value,
                "analysis",
                str(coefficient.value),
                spec.parts[-1],
            ),
            json_validator=spec.json_validator,
        )
        for coefficient in FEDPROX_COEFFICIENTS
        for spec in _stress_analysis_artifacts(Path("analysis"))
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            *artifacts,
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (
                    ExecutionRootDirectory.FEDPROX_STRESS_TEST.value,
                    PopulationId.NBAIOT_NATURAL_DEVICES.value,
                    "analysis",
                    ResearchArtifact.RESULTS.value,
                ),
                json_validator=_validate_model(MechanismPublicationDocument),
            ),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=(ExecutionRootDirectory.FEDPROX_STRESS_TEST.value,)),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _ditto_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.DITTO_ABSORPTION_STRESS_TEST
    artifacts = tuple(
        _artifact(
            spec.role,
            spec.kind,
            (
                ExecutionRootDirectory.DITTO_STRESS_TEST.value,
                PopulationId.NBAIOT_NATURAL_DEVICES.value,
                "analysis",
                str(regularization.value),
                spec.parts[-1],
            ),
            json_validator=spec.json_validator,
        )
        for regularization in DITTO_REGULARIZATION_GRID
        for spec in _stress_analysis_artifacts(Path("analysis"))
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            *artifacts,
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (
                    ExecutionRootDirectory.DITTO_STRESS_TEST.value,
                    PopulationId.NBAIOT_NATURAL_DEVICES.value,
                    "analysis",
                    ResearchArtifact.RESULTS.value,
                ),
                json_validator=_validate_model(MechanismPublicationDocument),
            ),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=(ExecutionRootDirectory.DITTO_STRESS_TEST.value,)),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _fine_tuning_contract() -> ExperimentEvidenceContract:
    experiment_id = ExperimentId.FEDAVG_LOCAL_FINE_TUNING
    parts = (
        ExecutionRootDirectory.FEDAVG_LOCAL_FINE_TUNING.value,
        PopulationId.NBAIOT_NATURAL_DEVICES.value,
        "analysis",
    )
    return ExperimentEvidenceContract(
        experiment=experiment_id,
        artifacts=(
            _artifact(
                ArtifactRole.RESULT_JSON,
                ArtifactKind.JSON,
                (*parts, ResearchArtifact.RESULTS.value),
                json_validator=_validate_model(MechanismPublicationDocument),
            ),
            _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, ResearchArtifact.EVIDENCE_REPORT.value)),
            _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, PUBLICATION_FILENAME)),
            _artifact(ArtifactRole.PUBLICATION, ArtifactKind.REPORT, (*parts, MECHANISM_REPORT_FILENAME)),
        ),
        owned_paths=(
            _evaluation_tree(experiment_id),
            OwnedPath(parts=(ExecutionRootDirectory.FEDAVG_LOCAL_FINE_TUNING.value,)),
            _progress_log(experiment_id),
        ),
        executes=True,
    )


def _stress_analysis_artifacts(directory: Path) -> tuple[ArtifactSpec, ...]:
    del directory
    return (
        _artifact(
            ArtifactRole.PUBLICATION,
            ArtifactKind.REPORT,
            (PUBLICATION_FILENAME,),
        ),
        _artifact(
            ArtifactRole.PUBLICATION,
            ArtifactKind.REPORT,
            (MECHANISM_REPORT_FILENAME,),
        ),
    )


def _validate_nonempty_json_object(path: Path) -> None:
    try:
        document = ExternalBenignStatisticsReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ArtifactIntegrityError(
            ErrorMessage(f"result JSON is missing, empty, or invalid: {path}"),
            subject=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        ) from error
    if not document.rows:
        raise ArtifactIntegrityError(
            ErrorMessage(f"result JSON does not contain experiment results: {path}"),
            subject=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        )


def _purge_retaining(path: Path, retain: frozenset[str]) -> None:
    if not path.is_dir():
        return
    for child in path.iterdir():
        if child.name in retain:
            continue
        if child.is_dir():
            rmtree(child)
        else:
            child.unlink()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
