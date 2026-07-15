from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.experiments.specifications import Q_SENSITIVITY_GRID, SweepAxis, SweepSpec
from datp_core.domain.thresholding.policies import ThresholdPercentile
from tests.unit.domain.test_protocol_aggregates import confirmatory_profile


@given(st.sampled_from(Q_SENSITIVITY_GRID))
def test_sweep_expansion_never_synthesizes_an_unauthorized_protocol(value: ThresholdPercentile) -> None:
    profile = confirmatory_profile()

    expanded = SweepSpec(axis=SweepAxis.QUANTILE, values=(value,)).expand(profile=profile)

    assert expanded == profile.authorized_protocols
    assert set(expanded).issubset(profile.authorized_protocols)
