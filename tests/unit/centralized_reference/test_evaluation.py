from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from tests.unit.centralized_reference.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    FEATURE_NAMES,
    benign_frame,
    mixed_evaluation_frame,
    require_cuda,
    run_miniature_training,
    training_coordinate,
)

from datp_core.centralized_reference.checkpointing import (
    retain_centralized_checkpoint_candidates,
)
from datp_core.centralized_reference.evaluation import (
    CentralizedConfusionCounts,
    evaluate_centralized_reference,
    reject_centralized_as_federated_threshold_policy,
    reject_centralized_in_federated_threshold_comparison,
    reject_centralized_result_in_confirmatory_threshold_comparison,
    reject_cross_client_cv_fpr_from_pooled_centralized,
)
from datp_core.centralized_reference.scoring import (
    CentralizedScoringRequest,
    score_centralized_reference,
)
from datp_core.centralized_reference.thresholding import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    construct_pooled_benign_quantile,
)
from datp_core.domain.enums import (
    CentralizedThresholdMethod,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, RowCount, Seed


def test_centralized_confusion_counts_require_row_count_values() -> None:
    confusion = CentralizedConfusionCounts(
        true_negative=RowCount(10),
        false_positive=RowCount(2),
        true_positive=RowCount(7),
        false_negative=RowCount(1),
    )
    assert sum(
        (
            confusion.true_negative,
            confusion.false_positive,
            confusion.true_positive,
            confusion.false_negative,
        )
    ) == RowCount(20)

    with pytest.raises(TypeError, match="RowCount"):
        CentralizedConfusionCounts(
            true_negative=cast(RowCount, 10),
            false_positive=RowCount(2),
            true_positive=RowCount(7),
            false_negative=RowCount(1),
        )


def test_pooled_evaluation_metrics_and_confusion(tmp_path: Path) -> None:
    require_cuda()
    execution = run_miniature_training(tmp_path / "train")
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)
    scoring = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=training_coordinate(),
            checkpoint=candidates[0],
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(RowCount(48), seed=Seed(9)),
            evaluation_features=mixed_evaluation_frame(RowCount(40), seed=Seed(10)),
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
    evaluation = evaluate_centralized_reference(
        coordinate=training_coordinate(),
        evaluation_scores=scoring.evaluation_scores,
        threshold_result=threshold,
    )
    assert evaluation.threshold_method is CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE
    assert evaluation.evidence_role is EvidenceRole.SUPPORTIVE
    assert evaluation.evaluation_row_count == 40
    assert (
        sum(
            (
                evaluation.confusion.true_negative,
                evaluation.confusion.false_positive,
                evaluation.confusion.true_positive,
                evaluation.confusion.false_negative,
            )
        )
        == 40
    )
    metric_ids = {item.metric for item in evaluation.metrics}
    assert MetricId.FALSE_POSITIVE_RATE in metric_ids
    assert MetricId.AUROC in metric_ids

    mismatched_scores = replace(
        scoring.evaluation_scores,
        checkpoint_checksum=Checksum("f" * 64),
    )
    with pytest.raises(ScientificContractError, match="frozen checkpoint"):
        evaluate_centralized_reference(
            coordinate=training_coordinate(),
            evaluation_scores=mismatched_scores,
            threshold_result=threshold,
        )


def test_rejects_confirmatory_and_federated_threshold_use(
    tmp_path: Path,
) -> None:
    require_cuda()
    execution = run_miniature_training(tmp_path / "train")
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)
    scoring = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=training_coordinate(),
            checkpoint=candidates[0],
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(RowCount(48), seed=Seed(11)),
            evaluation_features=mixed_evaluation_frame(RowCount(40), seed=Seed(12)),
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
    evaluation = evaluate_centralized_reference(
        coordinate=training_coordinate(),
        evaluation_scores=scoring.evaluation_scores,
        threshold_result=threshold,
    )
    with pytest.raises(
        LeakageError,
        match="confirmatory shared-versus-local",
    ):
        reject_centralized_result_in_confirmatory_threshold_comparison(evaluation)
    with pytest.raises(LeakageError, match="federated threshold policy"):
        reject_centralized_as_federated_threshold_policy(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
    with pytest.raises(LeakageError, match="CV\\(FPR\\)"):
        reject_cross_client_cv_fpr_from_pooled_centralized()
    with pytest.raises(
        LeakageError,
        match="federated threshold-policy comparisons",
    ):
        reject_centralized_in_federated_threshold_comparison(FederatedThresholdMethod.SHARED_THRESHOLD)
