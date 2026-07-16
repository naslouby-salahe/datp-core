from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.experiments.specifications import SweepAxis, SweepSpec
from tests.support.composed_configuration import composed_profile_catalogue
from tests.unit.domain.test_protocol_aggregates import confirmatory_profile


@given(data=st.data())
def test_sweep_expansion_never_synthesizes_an_unauthorized_protocol(data: st.DataObject) -> None:
    catalogue = composed_profile_catalogue()
    value = data.draw(st.sampled_from(catalogue.quantile_grid))
    profile = confirmatory_profile()

    expanded = SweepSpec(axis=SweepAxis.QUANTILE, values=(value,), catalogue=catalogue).expand(profile=profile)

    assert expanded == profile.authorized_protocols
    assert set(expanded).issubset(profile.authorized_protocols)
