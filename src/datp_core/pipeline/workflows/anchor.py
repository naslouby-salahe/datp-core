"""Historical anchor verification and independent-reproduction workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

from pydantic import ValidationError

from datp_core.anchor.comparison import (
    AnchorObservationSourceKind,
    AnchorObservedMetric,
)
from datp_core.anchor.gate import (
    AnchorGateDecision,
    AnchorGateStatus,
    assert_gate_not_bypassable,
    decide_anchor_gate,
    persist_anchor_gate_diagnostics,
)
from datp_core.anchor.reproduction import (
    ANCHOR_CHECKPOINT_STATUS,
    ANCHOR_EVIDENCE_ROLE,
    ANCHOR_METRIC,
    ANCHOR_POPULATION,
    ANCHOR_TRAINING_MODEL,
    AnchorDependencyBlocker,
    HistoricalMetricArtifactSource,
    independent_reproduction_dependency_blocker,
    load_historical_observations,
    reproduce_anchor,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    StageOperationId,
)
from datp_core.domain.errors import AnchorReproductionError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum, canonical_json_text
from datp_core.domain.values.base import NonNegativeIntegerValue
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.protocols.anchor import HISTORICAL_ANCHOR_SEED_COHORT, AnchorDecisionProtocol
from datp_core.protocols.seeds import SeedCohort
from datp_core.runtime.configuration import OUTPUTS_ROOT


class IndependentAnchorAssetName(StrEnum):
    ROOT = "independent"
    OBSERVATIONS = "independent_observations.json"
    COMPLETE = "COMPLETE"


class IndependentObservationPackage(StrictModel):
    observations: tuple[AnchorObservedMetric, ...]


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageRequest:
    protocol: AnchorDecisionProtocol
    observations: tuple[AnchorObservedMetric, ...] | None = None
    historical_sources: tuple[HistoricalMetricArtifactSource, ...] | None = None
    diagnostics_directory: Path | None = None
    request_independent_reproduction: bool = False
    independent_package_directory: Path | None = None


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageStatus:
    stage: ClassVar[StageOperationId] = StageOperationId.VERIFY_ANCHOR
    gate_status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    discrepancy_count: NonNegativeIntegerValue
    observation_count: NonNegativeIntegerValue
    reference_count: NonNegativeIntegerValue
    dependency_blocker: str | None
    diagnostics_checksum: Checksum


@dataclass(frozen=True, slots=True)
class VerifyAnchorStageResult:
    status: VerifyAnchorStageStatus
    gate: AnchorGateDecision


def independent_package_directory(output_root: Path = OUTPUTS_ROOT) -> Path:
    return output_root / "anchor" / IndependentAnchorAssetName.ROOT.value


def default_anchor_diagnostics_directory(output_root: Path = OUTPUTS_ROOT) -> Path:
    return output_root / "anchor" / "diagnostics"


def verify_anchor(request: VerifyAnchorStageRequest) -> VerifyAnchorStageResult:
    """Compare supplied or package-resolved observations against locked historical references."""
    observations, dependency_blocker = _resolve_observations(request)
    reproduction = reproduce_anchor(
        protocol=request.protocol,
        observations=observations,
        dependency_blocker=dependency_blocker,
    )
    decision = assert_gate_not_bypassable(decide_anchor_gate(reproduction))
    diagnostics_checksum = persist_anchor_gate_diagnostics(decision, request.diagnostics_directory)
    blocker_detail = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    status = VerifyAnchorStageStatus(
        gate_status=decision.status,
        dependent_readiness=decision.dependent_readiness,
        discrepancy_count=NonNegativeIntegerValue(len(decision.reproduction.discrepancies)),
        observation_count=NonNegativeIntegerValue(len(decision.reproduction.observations)),
        reference_count=NonNegativeIntegerValue(len(decision.reproduction.references)),
        dependency_blocker=blocker_detail,
        diagnostics_checksum=diagnostics_checksum,
    )
    return VerifyAnchorStageResult(status=status, gate=decision)


def observation_from_evaluation_document(
    document: FederatedEvaluationDocument,
    *,
    document_path: Path,
) -> AnchorObservedMetric:
    """Map one completed federated evaluation into an independent anchor observation."""
    if document.threshold_method not in {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    }:
        raise ScientificContractError(
            "independent anchor observations support only shared and local thresholds",
            subject=document.threshold_method,
        )
    coordinate = document.score_coordinate
    if coordinate.population is not ANCHOR_POPULATION:
        raise ScientificContractError(
            "independent anchor observation population must match the locked historical population",
            subject=coordinate.population,
        )
    if coordinate.model is not ANCHOR_TRAINING_MODEL:
        raise ScientificContractError(
            "independent anchor observation model must be FedAvg autoencoder",
            subject=coordinate.model,
        )
    value = population_metric(document, ANCHOR_METRIC)
    return AnchorObservedMetric(
        seed=coordinate.training_seed,
        population=ANCHOR_POPULATION,
        training_model=ANCHOR_TRAINING_MODEL,
        threshold_method=document.threshold_method,
        metric=ANCHOR_METRIC,
        value=value,
        checkpoint_status=ANCHOR_CHECKPOINT_STATUS,
        source_kind=AnchorObservationSourceKind.INDEPENDENT_REPRODUCTION,
        artifact_path=document_path.resolve(),
        artifact_checksum=checksum_file(document_path),
        model_checkpoint_identity=document.score_checkpoint_checksum,
        evidence_role=ANCHOR_EVIDENCE_ROLE,
    )


def load_independent_observations(package_directory: Path) -> tuple[AnchorObservedMetric, ...] | None:
    """Load a completed independent observation package, or None when absent."""
    document_path = package_directory / IndependentAnchorAssetName.OBSERVATIONS.value
    complete_path = package_directory / IndependentAnchorAssetName.COMPLETE.value
    if not document_path.is_file() or not complete_path.is_file():
        return None
    try:
        package = IndependentObservationPackage.model_validate_json(document_path.read_text(encoding="utf-8"))
        marker = complete_path.read_text(encoding="utf-8").strip()
        if marker != canonical_checksum(package).value:
            raise AnchorReproductionError(
                "independent observation package COMPLETE digest does not match payload",
                reason="stale_or_mismatched_artifact",
            )
    except AnchorReproductionError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, ValidationError) as error:
        raise AnchorReproductionError(
            "independent observation package is unreadable or invalid",
            reason="stale_or_mismatched_artifact",
        ) from error
    return package.observations


def publish_independent_observations(
    package_directory: Path,
    observations: tuple[AnchorObservedMetric, ...],
) -> Checksum:
    """Atomically publish the independent observation package with a COMPLETE digest."""
    if not observations:
        raise AnchorReproductionError(
            "independent observation package requires at least one observation",
            reason="missing_mandatory_observation",
        )
    package = IndependentObservationPackage(observations=observations)
    package_directory.mkdir(parents=True, exist_ok=True)
    document_path = package_directory / IndependentAnchorAssetName.OBSERVATIONS.value
    complete_path = package_directory / IndependentAnchorAssetName.COMPLETE.value
    digest = canonical_checksum(package)
    document_path.write_text(canonical_json_text(package), encoding="utf-8")
    complete_path.write_text(digest.value, encoding="utf-8")
    return digest


def collect_independent_observations_from_evaluations(
    *,
    output_root: Path,
    seed_cohort: SeedCohort = HISTORICAL_ANCHOR_SEED_COHORT,
) -> tuple[AnchorObservedMetric, ...]:
    """Load SHARED/LOCAL CV(FPR) evaluations for every historical seed as independent observations."""
    from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
    from datp_core.protocols.experiments import EXPERIMENTS

    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.HISTORICAL_DATP_REPRODUCTION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=seed_cohort,
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="independent anchor reproduction loads completed historical evaluation artifacts",
            ),
        ),
    )
    observations: list[AnchorObservedMetric] = []
    for entry in plan.entries:
        coordinate = entry.coordinate
        if coordinate.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
            continue
        if coordinate.threshold_method not in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }:
            continue
        document_path = (
            evaluation_run_directory(output_root, coordinate)
            / EvaluationRunAssetDirectory.EVALUATION
            / FederatedEvaluationAssetName.DOCUMENT
        )
        if not document_path.is_file():
            continue
        try:
            document = load_evaluation_document(document_path)
        except ScientificContractError:
            continue
        observations.append(observation_from_evaluation_document(document, document_path=document_path))
    return tuple(
        sorted(
            observations,
            key=lambda item: (item.seed.value, item.threshold_method.value),
        )
    )


def clear_independent_package(package_directory: Path) -> None:
    if package_directory.exists():
        rmtree(package_directory)


def _resolve_observations(
    request: VerifyAnchorStageRequest,
) -> tuple[tuple[AnchorObservedMetric, ...], AnchorDependencyBlocker | None]:
    if request.request_independent_reproduction and (
        request.observations is not None or request.historical_sources is not None
    ):
        raise AnchorReproductionError(
            "independent reproduction cannot be combined with historical sources or direct observations",
        )
    if request.observations is not None and request.historical_sources is not None:
        raise AnchorReproductionError("supply either typed observations or historical sources, not both")
    if request.observations is not None:
        return request.observations, None
    if request.historical_sources is not None:
        return load_historical_observations(request.historical_sources), None
    if request.request_independent_reproduction:
        package_directory = request.independent_package_directory
        if package_directory is None and request.diagnostics_directory is not None:
            package_directory = request.diagnostics_directory.parent / IndependentAnchorAssetName.ROOT.value
        if package_directory is None:
            package_directory = independent_package_directory()
        loaded = load_independent_observations(package_directory)
        if loaded is None or not loaded:
            return (), independent_reproduction_dependency_blocker()
        return loaded, None
    return (), independent_reproduction_dependency_blocker()
