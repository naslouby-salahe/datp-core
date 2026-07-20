"""Scientific fingerprint sensitivity to resolved record content."""

from datp_core.config.resolver import _unstructure, resolve_project_configuration
from datp_core.domain.catalogue import ModelArchitectureRecord
from datp_core.domain.fingerprints import compute_scientific_fingerprint
from datp_core.domain.values import PositiveInt


def _model(hidden: tuple[int, ...]) -> ModelArchitectureRecord:
    return ModelArchitectureRecord(
        identifier="fixed_autoencoder",
        kind="dense_autoencoder",
        hidden_dims=tuple(PositiveInt(d) for d in hidden),
        bottleneck_dim="last_hidden_dim",
        activation="relu",
        activation_placement="after_every_linear_layer_except_the_final_decoder_layer",
        output_activation="identity",
        normalization_layers="none",
        bias=True,
        reconstruction_objective="mse",
        training_loss_reduction="mean_over_all_elements_of_the_batch",
        precision="fp32",
        input_dimension_resolution="from_materialized_post_encoding_feature_schema",
        input_dimension_declared_per_dataset=False,
        input_dimension_validation="must_equal_materialization_post_encoding_feature_count",
        decoder_construction="mirrors_encoder_dimensions_in_reverse",
        decoder_final_layer_output_dim="input_dimension",
        weight_initialization="kaiming_uniform_fan_in_leaky_relu_negative_slope_sqrt_5",
        bias_initialization="uniform_symmetric_one_over_sqrt_fan_in",
        initialization_applied_to="every_linear_layer",
        initialization_seeded_by="training_seed",
        anomaly_score_definition="per_row_mean_of_squared_feature_reconstruction_error",
        anomaly_score_orientation="higher_score_means_more_anomalous",
    )


def test_scientific_fingerprint_changes_when_model_architecture_changes() -> None:
    baseline = compute_scientific_fingerprint({"model": _unstructure(_model((80, 40, 20)))})
    identical = compute_scientific_fingerprint({"model": _unstructure(_model((80, 40, 20)))})
    perturbed = compute_scientific_fingerprint({"model": _unstructure(_model((80, 40, 10)))})
    assert baseline == identical
    assert baseline != perturbed


def test_resolved_scientific_fingerprint_is_deterministic_across_resolutions() -> None:
    first = resolve_project_configuration().scientific_fingerprint
    second = resolve_project_configuration().scientific_fingerprint
    assert first == second
    assert len(first.value) == 64
