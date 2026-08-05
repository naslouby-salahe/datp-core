"""One-shot temporal reference and paired future-recalibration execution."""

from __future__ import annotations

from dataclasses import dataclass

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
    eligible_calibration_scores,
    family_identities,
    published_seed_directory,
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
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStateResult:
    state: TemporalState
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalFuturePairResult:
    frozen_future: TemporalStateResult
    recalibrated_future: TemporalStateResult


def run_temporal_static_reference_seed(partition_seed: Seed) -> TemporalStateResult:
    coordinate = _coordinate(partition_seed, TemporalState.STATIC_REFERENCE)
    context = resolve_execution_context(coordinate)
    scores = _score_context(context, coordinate)
    completed = _evaluate_state(
        context=context,
        identity=_execution_identity(coordinate),
        scores=scores,
        calibration_role=PartitionRole.CALIBRATION,
        provenance=None,
    )
    return TemporalStateResult(
        state=TemporalState.STATIC_REFERENCE,
        completed_threshold_methods=completed,
    )


def run_temporal_future_pair(partition_seed: Seed) -> TemporalFuturePairResult:
    frozen_coordinate = _coordinate(partition_seed, TemporalState.FROZEN_FUTURE)
    context = resolve_execution_context(frozen_coordinate)
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
        provenance=frozen_provenance,
    )
    recalibrated_coordinate = _coordinate(partition_seed, TemporalState.RECALIBRATED_FUTURE)
    recalibrated = _evaluate_state(
        context=context,
        identity=_execution_identity(recalibrated_coordinate),
        scores=scores,
        calibration_role=PartitionRole.FUTURE_RECALIBRATION,
        provenance=recalibrated_provenance,
    )
    return TemporalFuturePairResult(
        frozen_future=TemporalStateResult(
            state=TemporalState.FROZEN_FUTURE,
            completed_threshold_methods=frozen,
        ),
        recalibrated_future=TemporalStateResult(
            state=TemporalState.RECALIBRATED_FUTURE,
            completed_threshold_methods=recalibrated,
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
    provenance: TemporalDeploymentProvenance | None,
) -> tuple[FederatedThresholdMethod, ...]:
    eligible = eligible_calibration_scores(scores, calibration_role)
    families = family_identities(context.clients, context.family_by_client)
    capabilities = population_capabilities(context.coordinate.population)
    previous_evidence: FixedScoreEvidence | None = None
    completed: list[FederatedThresholdMethod] = []
    for method in capabilities.valid_threshold_methods:
        threshold = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    method,
                    context.coordinate,
                    CANONICAL_QUANTILE,
                    capabilities,
                    eligible,
                    families,
                ),
                output_directory=published_seed_directory(identity, context.coordinate.training_seed)
                / "thresholds"
                / method.value,
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
                comparison_fixed_score_evidence=previous_evidence,
                evidence_role=identity.evidence_role,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=identity,
                temporal_provenance=provenance,
                temporal_threshold_provenance=provenance,
                output_directory=published_seed_directory(identity, context.coordinate.training_seed)
                / "evaluations"
                / method.value,
                overwrite=False,
            )
        )
        if not evaluation.complete_digest.value:
            raise ScientificContractError("temporal evaluation produced an empty completion digest")
        previous_evidence = evaluation_inputs.fixed_score_evidence
        completed.append(method)
    return tuple(completed)


def _execution_identity(coordinate: ExperimentCoordinate) -> ExternalTemporalExecutionIdentity:
    if coordinate.temporal_state is None:
        raise ScientificContractError("temporal execution requires a temporal state")
    return ExternalTemporalExecutionIdentity(
        experiment=coordinate.experiment,
        population=coordinate.population,
        evidence_role=coordinate.evidence_role,
        temporal_state=coordinate.temporal_state,
    )


def _coordinate(partition_seed: Seed, state: TemporalState) -> ExperimentCoordinate:
    declaration = _temporal_declaration()
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
