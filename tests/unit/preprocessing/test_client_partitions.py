import polars as pl

from datp_core.domain.enums import DatasetId, PopulationId
from datp_core.domain.values.identifiers import FeatureName, FeatureNameSequence
from datp_core.preprocessing.client_partitions import exclude_nonfinite_model_input_rows


def _feature_names(*names: str) -> FeatureNameSequence:
    return FeatureNameSequence(tuple(FeatureName(name) for name in names))


def test_excludes_row_with_null_numeric_model_input_feature() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b", "c"],
            "feature_one": [1.0, None, 3.0],
            "feature_two": [4.0, 5.0, 6.0],
        }
    )

    eligible = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one", "feature_two"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_GROUPS,
    )

    assert eligible.get_column("stable_row_id").to_list() == ["a", "c"]


def test_excludes_row_with_non_finite_numeric_model_input_feature() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b"],
            "feature_one": [1.0, float("inf")],
        }
    )

    eligible = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_GROUPS,
    )

    assert eligible.get_column("stable_row_id").to_list() == ["a"]


def test_never_fills_or_fabricates_a_replacement_value() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b"],
            "feature_one": [1.0, None],
        }
    )

    eligible = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_GROUPS,
    )

    assert eligible.get_column("feature_one").null_count() == 0
    assert eligible.height == 1


def test_all_rows_retained_when_every_feature_is_finite() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b"],
            "feature_one": [1.0, 2.0],
        }
    )

    eligible = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_GROUPS,
    )

    assert eligible.height == joined.height
