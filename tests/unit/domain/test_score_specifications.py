from dataclasses import fields

from datp_core.domain.learning.scores import (
    ClientCalibrationScoreArtifact,
    ClientTemporalScoreArtifact,
    ClientTestScoreArtifact,
    ScoreGenerationSpec,
    ScoringBatchSpec,
    SplitScopedScoreBundle,
)


def test_calibration_score_artifact_has_no_attack_surface() -> None:
    field_names = {entry.name for entry in fields(ClientCalibrationScoreArtifact)}

    assert all("attack" not in name for name in field_names)


def test_test_score_artifact_exposes_one_citable_aggregate_identity() -> None:
    field_names = {entry.name for entry in fields(ClientTestScoreArtifact)}

    assert "aggregate_manifest_hash" in field_names
    assert "benign_scores_identity" not in field_names
    assert "attack_scores_identity" not in field_names
    assert {"benign_scores_ref", "attack_scores_ref"} <= field_names


def test_scoring_ownership_and_role_types_are_structurally_distinct() -> None:
    assert {entry.name for entry in fields(ScoreGenerationSpec)} == {
        "scoring_batch",
        "precision",
        "numeric_equivalence_policy",
    }
    assert {entry.name for entry in fields(ScoringBatchSpec)} == {
        "calibration_batch_size",
        "test_batch_size",
        "temporal_batch_size",
    }
    assert ClientCalibrationScoreArtifact is not ClientTestScoreArtifact
    assert ClientTestScoreArtifact is not ClientTemporalScoreArtifact
    assert {entry.name for entry in fields(SplitScopedScoreBundle)} == {"calibration", "test", "temporal"}
