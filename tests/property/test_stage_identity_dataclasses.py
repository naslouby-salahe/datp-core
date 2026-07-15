from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
)
from datp_core.domain.artifacts.lineage import (
    TestScoringIdentity as ScoringTestIdentity,
)
from datp_core.domain.artifacts.references import StageFingerprint


@given(st.text(alphabet="0123456789abcdef", min_size=64, max_size=64))
def test_identity_wrapping_is_stable_for_generated_fingerprints(value: str) -> None:
    fingerprint = StageFingerprint(value=value)
    calibration_scoring_identity = CalibrationScoringIdentity(value=fingerprint)
    repeated_calibration_scoring_identity = CalibrationScoringIdentity(value=fingerprint)
    scoring_test_identity = ScoringTestIdentity(value=fingerprint)
    repeated_scoring_test_identity = ScoringTestIdentity(value=fingerprint)

    assert calibration_scoring_identity == repeated_calibration_scoring_identity
    assert scoring_test_identity == repeated_scoring_test_identity
