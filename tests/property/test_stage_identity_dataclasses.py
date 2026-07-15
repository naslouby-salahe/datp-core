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

    assert CalibrationScoringIdentity(value=fingerprint) == CalibrationScoringIdentity(value=fingerprint)
    assert ScoringTestIdentity(value=fingerprint) == ScoringTestIdentity(value=fingerprint)
