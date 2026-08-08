from pathlib import Path

import pytest

from datp_core.core.identifiers import SplitProtocolId
from datp_core.data.preprocessing.paths import build_preprocessed_partition_paths


@pytest.mark.parametrize(
    ("split_protocol", "optional_roles_present"),
    (
        (SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS, frozenset()),
        (SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE, frozenset({"future_recalibration"})),
        (SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE, frozenset({"static_reference_reserve"})),
    ),
)
def test_build_preprocessed_partition_paths_matches_prior_construction(
    split_protocol: SplitProtocolId, optional_roles_present: frozenset[str]
) -> None:
    coordinate_directory = Path("data/processed/example")

    result = build_preprocessed_partition_paths(coordinate_directory, split_protocol)

    assert result.train == coordinate_directory / "train.parquet"
    assert result.calibration == coordinate_directory / "calibration.parquet"
    assert result.evaluation == coordinate_directory / "evaluation.parquet"
    assert (result.future_recalibration is not None) == ("future_recalibration" in optional_roles_present)
    assert (result.static_reference_reserve is not None) == ("static_reference_reserve" in optional_roles_present)
    if result.future_recalibration is not None:
        assert result.future_recalibration == coordinate_directory / "future_recalibration.parquet"
    if result.static_reference_reserve is not None:
        assert result.static_reference_reserve == coordinate_directory / "static_reference_reserve.parquet"
