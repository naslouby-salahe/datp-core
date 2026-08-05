"""One-shot temporal reference and paired future-recalibration execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    validate_frozen_recalibrated_pair,
)
from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    PartitionRole,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.evaluation.controls import FixedScoreEvidence, build_federated_evaluation_inputs
from datp_core.pipeline.construct_thresholds import ConstructFederatedThresholdsRequest, construct_federated_thresholds
from datp_core.pipeline.evaluate_detector import EvaluateFederatedDetectorRequest, evaluate_federated_detector
from datp_core.pipeline.federated_execution import (
    FederatedExecutionContext,
    bounded_evidence_seed_directory,
    eligible_calibration_scores,
    resolve_execution_context,
    score_execution_context,
    training_autoencoder,
    training_feature_names,
)
from datp_core.pipeline.planning import ExperimentCoordinate, expand_experiment_plan
from datp_core.pipeline.scoring.service import FederatedScoreArtifactManifest
from datp_core.populations.capabilities import population_capabilities
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.experiments import EXPERIMENTS, ExternalTemporalExecutionIdentity
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.runtime import OUTPUTS_ROOT
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult


class TemporalArtifactDirectory(StrEnum):
    THRESHOLDS = "thresholds"
    EVALUATIONS = "evaluations"


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStateResult:
    state: TemporalState
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalFuturePairResult:
    frozen_future: TemporalStateResult
    recalibrated_future: TemporalStateResult


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStateExecution:
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]
    fixed_score_evidence: FixedScoreEvidence


def run_temporal_static_reference_seed(partition_seed: Seed) -> TemporalStateResult:
    declaration = _temporal_declaration()
    coordinate = _coordinate(partition_seed, TemporalState.STATIC_REFERENCE, declaration)
    context = resolve_execution_context(coordinate, OUTPUTS_ROOT)
    scores = _score_context(context, coordinate)
    execution = _evaluate_state(
        context=context,
        identity=_execution_identity(coordinate),
        scores=scores,
        calibration_role=PartitionRole.CALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=None,
        comparison_fixed_score_evidence=None,
    )
    return TemporalStateResult(
        state=TemporalState.STATIC_REFERENCE,
        completed_threshold_methods=execution.completed_threshold_methods,
    )


def run_temporal_future_pair(partition_seed: Seed) -> TemporalFuturePairResult:
    declaration = _temporal_declaration()
    frozen_coordinate = _coordinate(partition_seed, TemporalState.FROZEN_FUTURE, declaration)
    context = resolve_execution_context(frozen_coordinate, OUTPUTS_ROOT)
    scores = _score_context(context, frozen_coordinate)
    frozen_provenance = TemporalDeploymentProvenance.from_score_manifest(TemporalState.FROZEN_FUTURE, scores)
    recalibrated_provenance = TemporalDeploymentProvenance.from_score_manifest(
        TemporalState.RECALIBRATED_FUTURE,
        scores,
    )
    validate_frozen_recalibrated_pair(frozen_provenance, recalibrated_provenance)
    frozen = _evaluate_state(
        context=context,
        identity=_execution_identity(frozen_coordinate),
        scores=scores,
        calibration_role=PartitionRole.CALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=frozen_provenance,
        comparison_fixed_score_evidence=None,
    )
    recalibrated_coordinate = _coordinate(
        partition_seed,
        TemporalState.RECALIBRATED_FUTURE,
        declaration,
    )
    recalibrated = _evaluate_state(
        context=context,
        identity=_execution_identity(recalibrated_coordinate),
        scores=scores,
        calibration_role=PartitionRole.FUTURE_RECALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=recalibrated_provenance,
        comparison_fixed_score_evidence=frozen.fixed_score_evidence,
    )
    return TemporalFuturePairResult(
        frozen_future=TemporalStateResult(
            state=TemporalState.FROZEN_FUTURE,
            completed_threshold_methods=frozen.completed_threshold_methods,
        ),
        recalibrated_future=TemporalStateResult(
            state=TemporalState.RECALIBRATED_FUTURE,
            completed_threshold_methods=recalibrated.completed_threshold_methods,
        ),
    )


def _score_context(
    context: FederatedExecutionContext,
    coordinate: ExperimentCoordinate,
) -> FederatedScoreArtifactManifest:
    return score_execution_context(
        context,
        autoencoder=training_autoencoder(coordinate.dataset),
        feature_names=training_feature_names(coordinate.dataset),
    )


def _evaluate_state(
    *,
    context: FederatedExecutionContext,
    identity: ExternalTemporalExecutionIdentity,
    scores: FederatedScoreArtifactManifest,
    calibration_role: PartitionRole,
    threshold_methods: tuple[FederatedThresholdMethod, ...],
    provenance: TemporalDeploymentProvenance | None,
    comparison_fixed_score_evidence: FixedScoreEvidence | None,
) -> TemporalStateExecution:
    eligible = eligible_calibration_scores(scores, calibration_role)
    capabilities = population_capabilities(context.coordinate.population)
    reference_evidence = comparison_fixed_score_evidence
    observed_evidence: FixedScoreEvidence | None = None
    completed: list[FederatedThresholdMethod] = []
    output_root = bounded_evidence_seed_directory(
        identity,
        context.coordinate.training_seed,
        OUTPUTS_ROOT,
    )
    for method in threshold_methods:
        threshold = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    method,
                    context.coordinate,
                    CANONICAL_QUANTILE,
                    capabilities,
                    eligible,
                    context.family_by_client,
                ),
                output_directory=(
                    output_root / TemporalArtifactDirectory.THRESHOLDS.value / method.value
                ),
                overwrite=False,
                temporal_provenance=provenance,
                temporal_score_manifest=scores if provenance is not None else None,
            )
        ).result
        if isinstance(threshold, ThresholdUnavailableResult):
            continue
        evaluation_inputs = build_federated_evaluation_inputs(scores, method)
        evaluation = evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                score_manifest=scores,
                threshold_result=threshold,
                cohort=evaluation_inputs.cohort,
                fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
                comparison_fixed_score_evidence=reference_evidence,
                evidence_role=identity.evidence_role,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=identity,
                temporal_provenance=provenance,
                temporal_threshold_provenance=provenance,
                output_directory=(
                    output_root / TemporalArtifactDirectory.EVALUATIONS.value / method.value
                ),
                overwrite=False,
            )
        )
        if not evaluation.complete_digest.value:
            raise ScientificContractError("temporal evaluation produced an empty completion digest")
        observed_evidence = evaluation_inputs.fixed_score_evidence
        if reference_evidence is None:
            reference_evidence = observed_evidence
        completed.append(method)
    if observed_evidence is None or not completed:
        raise ScientificContractError(
            "temporal execution produced no evaluable threshold method",
            subject=identity.temporal_state,
        )
    return TemporalStateExecution(
        completed_threshold_methods=tuple(completed),
        fixed_score_evidence=observed_evidence,
    )


def _execution_identity(coordinate: ExperimentCoordinate) -> ExternalTemporalExecutionIdentity:
    if coordinate.temporal_state is None:
        raise ScientificContractError("temporal execution requires a temporal state")
    return ExternalTemporalExecutionIdentity(
        experiment=coordinate.experiment,
        population=coordinate.population,
        evidence_role=coordinate.evidence_role,
        temporal_state=coordinate.temporal_state,
    )


def _coordinate(
    partition_seed: Seed,
    state: TemporalState,
    declaration: ExperimentDeclaration,
) -> ExperimentCoordinate:
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
    )
    matches = tuple(entry.coordinate for entry in plan.entries if entry.coordinate.temporal_state is state)
    if not matches:
        raise ScientificContractError(f"no temporal coordinate is declared for {state.value}")
    first = matches[0]
    if any(
        candidate.dataset is not first.dataset
        or candidate.population is not first.population
        or candidate.split_protocol is not first.split_protocol
        or candidate.preprocessing_protocol is not first.preprocessing_protocol
        or candidate.training_model is not first.training_model
        for candidate in matches[1:]
    ):
        raise ScientificContractError(f"temporal coordinates disagree on detector identity for {state.value}")
    return first


def _temporal_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    if len(matches) != 1:
        raise ScientificContractError("the temporal experiment must be declared exactly once")
    return matches[0]
