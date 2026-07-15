from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
    CentralizedCalibrationScoringIdentity,
    CentralizedModelIdentity,
    CheckpointIdentity,
    CheckpointSelectionIdentity,
    DatasetSourceIdentity,
    EvaluationIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    PartitionIdentity,
    ProcessedSplitIdentity,
    ReportIdentity,
    ResultFreezeIdentity,
    SplitIdentity,
    StageIdentity,
    StatisticalIdentity,
    TemporalScoringIdentity,
    ThresholdIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.lineage import (
    TestScoringIdentity as ScoringTestIdentity,
)
from datp_core.domain.artifacts.references import StageFingerprint


def _fingerprint(value: str) -> StageFingerprint:
    return StageFingerprint(value=value * 64)


def _requires_test_identity(*, identity: ScoringTestIdentity) -> ScoringTestIdentity:
    return identity


def test_stage_identity_roles_are_nominally_distinct_at_runtime() -> None:
    calibration = CalibrationScoringIdentity(value=_fingerprint("a"))
    test = ScoringTestIdentity(value=_fingerprint("a"))

    assert calibration != test
    assert _requires_test_identity(identity=test) is test
    assert CalibrationScoringIdentity is not ScoringTestIdentity


def test_centralized_identities_are_not_accepted_by_federated_contracts() -> None:
    centralized = CentralizedModelIdentity(value=_fingerprint("b"))

    assert CentralizedModelIdentity is not TrainingIdentity
    assert centralized != TrainingIdentity(value=_fingerprint("b"))
    assert CentralizedCalibrationScoringIdentity is not CalibrationScoringIdentity


def test_stage_identity_composes_each_scoring_role_explicitly() -> None:
    stage_identity = StageIdentity(
        dataset_source=DatasetSourceIdentity(value=_fingerprint("0")),
        feature_schema=FeatureSchemaIdentity(value=_fingerprint("1")),
        partition=PartitionIdentity(value=_fingerprint("2")),
        split=SplitIdentity(value=_fingerprint("3")),
        fitted_preprocessor=FittedPreprocessorIdentity(value=_fingerprint("4")),
        processed_split=ProcessedSplitIdentity(value=_fingerprint("5")),
        training=TrainingIdentity(value=_fingerprint("6")),
        checkpoint=CheckpointIdentity(value=_fingerprint("7")),
        checkpoint_selection=CheckpointSelectionIdentity(value=_fingerprint("8")),
        calibration_scoring=CalibrationScoringIdentity(value=_fingerprint("a")),
        test_scoring=ScoringTestIdentity(value=_fingerprint("b")),
        temporal_scoring=TemporalScoringIdentity(value=_fingerprint("c")),
        threshold=ThresholdIdentity(value=_fingerprint("d")),
        evaluation=EvaluationIdentity(value=_fingerprint("e")),
        statistical=StatisticalIdentity(value=_fingerprint("f")),
        result_freeze=ResultFreezeIdentity(value=_fingerprint("9")),
        report=ReportIdentity(value=_fingerprint("a")),
    )

    assert stage_identity.calibration_scoring.value != stage_identity.test_scoring.value
    assert stage_identity.training.value != stage_identity.calibration_scoring.value
