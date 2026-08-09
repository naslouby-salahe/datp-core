from datp_core.core.identifiers import SplitProtocolId
from datp_core.core.numeric import RowCount
from datp_core.data.populations.splits import hamilton_integer_counts, static_reference_split_protocol


def test_temporal_ratio_contract_is_exact() -> None:
    assert SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE.value == "random_fractional_static_reference"
    assert hamilton_integer_counts(RowCount(20), (0.55, 0.15, 0.10, 0.20)) == (
        RowCount(11),
        RowCount(3),
        RowCount(2),
        RowCount(4),
    )
    protocol = static_reference_split_protocol()
    assert (protocol.training.value, protocol.calibration.value, protocol.reserve.value, protocol.evaluation.value) == (
        0.55,
        0.15,
        0.10,
        0.20,
    )
