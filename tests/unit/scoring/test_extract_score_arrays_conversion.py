import numpy as np
import polars as pl
from tests.unit.learning.federated.helpers import FEATURE_NAMES

from datp_core.core.numeric import RowCount, Seed
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
)
from datp_core.detector.scoring.frames import extract_score_arrays


def _float64_benign_frame(row_count: RowCount, seed: Seed) -> pl.DataFrame:
    generator = np.random.default_rng(seed.value)
    matrix = generator.normal(size=(row_count.value, len(FEATURE_NAMES))).astype(np.float64)
    return pl.DataFrame(
        {
            STABLE_ROW_ID_COLUMN: [f"row-{seed.value}-{index}" for index in range(row_count.value)],
            OUTCOME_LABEL_COLUMN: [PopulationOutcomeLabel.BENIGN.value] * row_count.value,
            **{name: matrix[:, index] for index, name in enumerate(FEATURE_NAMES.names)},
        },
        schema_overrides={name: pl.Float64 for name in FEATURE_NAMES.names},
    )


def test_extract_score_arrays_matches_the_naive_polars_to_numpy_astype_conversion() -> None:
    frame = _float64_benign_frame(RowCount(64), Seed(1))

    arrays = extract_score_arrays(frame, FEATURE_NAMES)

    reference = frame.select(FEATURE_NAMES.as_list()).to_numpy().astype(np.float32, copy=False)

    assert arrays.feature_matrix.dtype == np.float32
    assert arrays.feature_matrix.shape == reference.shape
    assert np.array_equal(arrays.feature_matrix, reference)


def test_extract_score_arrays_feature_matrix_is_writable_and_does_not_alias_the_source_frame() -> None:
    frame = _float64_benign_frame(RowCount(16), Seed(2))

    arrays = extract_score_arrays(frame, FEATURE_NAMES)

    assert arrays.feature_matrix.flags.writeable
    original_first_value = frame.get_column(FEATURE_NAMES.names[0])[0]
    arrays.feature_matrix[0, 0] = 12345.0
    assert frame.get_column(FEATURE_NAMES.names[0])[0] == original_first_value
