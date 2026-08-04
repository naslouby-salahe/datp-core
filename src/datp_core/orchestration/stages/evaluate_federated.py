"""Stage: compose held-out federated evaluation publication."""

from datp_core.domain.values import checksum_file
from datp_core.evaluation.population import (
    FederatedEvaluationArtifacts,
    FederatedEvaluationAssetName,
    FederatedEvaluationRequest,
    federated_evaluation_is_reusable,
    load_reused_federated_evaluation,
    prepare_federated_evaluation,
    rebase_federated_evaluation,
    write_federated_evaluation,
)
from datp_core.orchestration.commands.evaluation import (
    EvaluateFederatedRequest as _EvaluateFederatedRequest,
    FederatedEvaluationResult as _FederatedEvaluationResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)


def evaluate_federated_stage(
    request: _EvaluateFederatedRequest,
) -> _FederatedEvaluationResult:
    evaluation_request = FederatedEvaluationRequest(
        score_manifest=request.score_manifest,
        threshold_result=request.threshold_result,
        cohort=request.cohort,
        fixed_score_evidence=request.fixed_score_evidence,
        comparison_fixed_score_evidence=request.comparison_fixed_score_evidence,
        evidence_role=request.evidence_role,
        conformal_coverage_inputs=request.conformal_coverage_inputs,
        threshold_estimation_inputs=request.threshold_estimation_inputs,
        communication_messages=request.communication_messages,
        traffic_rate_evidence=request.traffic_rate_evidence,
        temporal_provenance=request.temporal_provenance,
        temporal_threshold_provenance=request.temporal_threshold_provenance,
        execution_identity=request.execution_identity,
    )
    prepared = prepare_federated_evaluation(evaluation_request)
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=write_federated_evaluation,
                validator=federated_evaluation_is_reusable,
                loader=load_reused_federated_evaluation,
                rebaser=rebase_federated_evaluation,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedEvaluationAssetName.COMPLETE,
        )
    )
    artifacts: FederatedEvaluationArtifacts = publication.value
    return _FederatedEvaluationResult(
        publication_status=publication.status,
        clients=artifacts.clients,
        population=artifacts.population,
        diagnostics=artifacts.diagnostics,
        complete_digest=checksum_file(
            request.output_directory / FederatedEvaluationAssetName.COMPLETE
        ),
    )
