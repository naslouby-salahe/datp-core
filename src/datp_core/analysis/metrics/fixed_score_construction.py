from datp_core.analysis.metrics.cohort_construction import assert_cohort_invariant_to_threshold_methods
from datp_core.analysis.metrics.cohort_evidence import client_partition_counts_from_scores
from datp_core.analysis.metrics.fixed_score import FederatedEvaluationInputs, FixedScoreEvidence
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, PartitionRole
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.models import FederatedTrainingCoordinate

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


def build_federated_evaluation_inputs(
    score_manifest: FederatedScoreArtifactManifest,
    threshold_method: FederatedThresholdMethod,
    *,
    calibration_role: PartitionRole = PartitionRole.CALIBRATION,
) -> FederatedEvaluationInputs:
    if calibration_role not in {PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION}:
        raise ScientificContractError(ErrorMessage("evaluation inputs require a calibration partition role"))
    if not score_manifest.records_for(calibration_role):
        raise ScientificContractError(ErrorMessage("evaluation inputs require the declared calibration score set"))
    cohort = assert_cohort_invariant_to_threshold_methods(
        population=score_manifest.coordinate.population,
        partition_seed=score_manifest.coordinate.training_seed,
        client_counts=client_partition_counts_from_scores(score_manifest),
        methods=(threshold_method,),
    )
    return FederatedEvaluationInputs(
        cohort=cohort,
        fixed_score_evidence=FixedScoreEvidence(
            threshold_method=threshold_method,
            calibration_role=calibration_role,
            score_manifest=score_manifest,
        ),
    )
