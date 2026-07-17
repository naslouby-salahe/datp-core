from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.data.preprocessing import FittedStatisticPolicy, NormalizationScope, NormalizationStrategy
from datp_core.infrastructure.data.nbaiot.preprocessing import is_authorized_nbaiot_policy

_ONLY_AUTHORIZED_COMBINATION = (
    NormalizationStrategy.STANDARD,
    NormalizationScope.PER_CLIENT_TRAIN,
    FittedStatisticPolicy.EXACT_TWO_PASS,
)


@given(
    strategy=st.sampled_from(NormalizationStrategy),
    scope=st.sampled_from(NormalizationScope),
    fitted_stat_policy=st.sampled_from(FittedStatisticPolicy),
)
def test_only_the_recovered_nbaiot_policy_combination_is_authorized(
    strategy: NormalizationStrategy, scope: NormalizationScope, fitted_stat_policy: FittedStatisticPolicy
) -> None:
    authorized = is_authorized_nbaiot_policy(strategy=strategy, scope=scope, fitted_stat_policy=fitted_stat_policy)

    assert authorized is ((strategy, scope, fitted_stat_policy) == _ONLY_AUTHORIZED_COMBINATION)
