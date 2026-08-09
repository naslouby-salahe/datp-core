from dataclasses import replace
from pathlib import Path

import pytest
from tests.unit.learning.centralized.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    FEATURE_NAMES,
    benign_frame,
    mixed_evaluation_frame,
    require_cuda,
    run_miniature_training,
    training_coordinate,
)

from datp_core.analysis.metrics.models import ConfusionCounts
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import CentralizedThresholdMethod, EvidenceRole, MetricId
from datp_core.core.numeric import RowCount, Seed
from datp_core.detector.checkpoints.service import retain_centralized_checkpoint_candidates
from datp_core.detector.scoring.centralized import score_centralized_reference
from datp_core.detector.scoring.models import CentralizedScoringRequest
from datp_core.thresholds.centralized import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    CentralizedDecisionRule,
    CentralizedEvaluationResult,
    construct_pooled_benign_quantile,
    evaluate_centralized_reference,
    threshold_result_checksum,
)


def test_centralized_evaluation_rejects_invalid_attack_assignment(tmp_path: Path) -> None:
    require_cuda()
    _, threshold, evaluation = _evaluation(tmp_path, 13, 14)
    invalid_confusion = ConfusionCounts(
        true_negative=RowCount(10),
        false_positive=RowCount(2),
        true_positive=RowCount(0),
        false_negative=RowCount(0),
        attack_assignment_valid=False,
    )
    threshold_checksum = threshold_result_checksum(threshold)
    with pytest.raises(ScientificContractError, match="valid attack assignment"):
        CentralizedEvaluationResult(
            coordinate=evaluation.coordinate,
            threshold_method=evaluation.threshold_method,
            decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
            threshold=evaluation.threshold,
            confusion=invalid_confusion,
            metrics=evaluation.metrics,
            evaluation_row_count=invalid_confusion.evaluation_row_count,
            evidence_role=EvidenceRole.SUPPORTIVE,
            score_artifact_checksum=evaluation.score_artifact_checksum,
            threshold_checksum=threshold_checksum,
        )


def _evaluation(tmp_path: Path, calibration_seed: int, evaluation_seed: int):
    execution = run_miniature_training(tmp_path / "train")
    training = execution.result
    candidate = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)[0]
    scoring = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=training_coordinate(),
            checkpoint=candidate,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(RowCount(48), seed=Seed(calibration_seed)),
            evaluation_features=mixed_evaluation_frame(RowCount(40), seed=Seed(evaluation_seed)),
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_checksum=training.preprocessing_state_checksum,
        )
    )
    threshold = construct_pooled_benign_quantile(
        coordinate=training_coordinate(),
        calibration_scores=scoring.calibration_scores,
        protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    )
    return (
        scoring,
        threshold,
        evaluate_centralized_reference(
            coordinate=training_coordinate(),
            evaluation_scores=scoring.evaluation_scores,
            threshold_result=threshold,
        ),
    )


def test_pooled_evaluation_metrics_and_confusion(tmp_path: Path) -> None:
    require_cuda()
    scoring, threshold, evaluation = _evaluation(tmp_path, 9, 10)
    assert evaluation.threshold_method is CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE
    assert evaluation.evidence_role is EvidenceRole.SUPPORTIVE
    assert evaluation.evaluation_row_count.value == 40
    assert MetricId.AUROC in {item.metric for item in evaluation.metrics}
    coordinate = training_coordinate()
    evaluation_scores = replace(scoring.evaluation_scores, checkpoint_checksum=Checksum("f" * 64))
    with pytest.raises(ScientificContractError, match="frozen checkpoint"):
        evaluate_centralized_reference(
            coordinate=coordinate,
            evaluation_scores=evaluation_scores,
            threshold_result=threshold,
        )
