from datp_core.domain.enums import SplitProtocolId
from datp_core.populations.models import hamilton_integer_counts
from datp_core.populations.splits import static_reference_split_protocol


def test_temporal_ratio_contract_is_exact() -> None:
    assert SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE.value == "random_fractional_static_reference"
    assert hamilton_integer_counts(20, (0.55, 0.15, 0.10, 0.20)) == (11, 3, 2, 4)
    protocol = static_reference_split_protocol()
    assert (protocol.training.value, protocol.calibration.value, protocol.reserve.value, protocol.evaluation.value) == (
        0.55,
        0.15,
        0.10,
        0.20,
    )
