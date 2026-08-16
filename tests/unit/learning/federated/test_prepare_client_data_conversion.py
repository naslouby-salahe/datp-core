import numpy as np
import polars as pl
import torch
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    FEATURE_NAMES,
    client_identity,
    fitted_state,
)

from datp_core.core.numeric import RowCount, Seed
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
)
from datp_core.detector.autoencoder import TORCH_LEARNING_DTYPE
from datp_core.detector.training.engine import prepare_federated_client_data
from datp_core.detector.training.models import ClientTrainingInput


def _float64_frame(row_count: RowCount, seed: Seed) -> pl.DataFrame:
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


def test_prepare_federated_client_data_matches_the_naive_polars_to_numpy_astype_conversion(tmp_path) -> None:
    state = fitted_state(tmp_path / "client_state.skops", "client_a")
    training_frame = _float64_frame(RowCount(20), Seed(3))
    validation_frame = _float64_frame(RowCount(10), Seed(4))
    client_input = ClientTrainingInput(
        client=client_identity("client_a"),
        training_features=training_frame,
        validation_features=validation_frame,
        feature_names=FEATURE_NAMES,
        preprocessing_state=state,
    )

    prepared = prepare_federated_client_data(client_input, AUTOENCODER)

    reference_matrix = training_frame.select(FEATURE_NAMES.as_list()).to_numpy().astype(np.float32, copy=False)
    reference_validation_matrix = (
        validation_frame.select(FEATURE_NAMES.as_list()).to_numpy().astype(np.float32, copy=False)
    )
    reference_tensor = torch.as_tensor(reference_matrix, dtype=TORCH_LEARNING_DTYPE, device="cpu")
    reference_validation_tensor = torch.as_tensor(reference_validation_matrix, dtype=TORCH_LEARNING_DTYPE, device="cpu")

    assert prepared.features_cpu.dtype == TORCH_LEARNING_DTYPE
    assert prepared.validation_features_cpu.dtype == TORCH_LEARNING_DTYPE
    assert torch.equal(prepared.features_cpu.cpu(), reference_tensor)
    assert torch.equal(prepared.validation_features_cpu.cpu(), reference_validation_tensor)
