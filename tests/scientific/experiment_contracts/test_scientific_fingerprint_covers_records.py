"""Scientific fingerprint sensitivity to resolved record content."""

from datp_core.config.fingerprinting.canonical import compute_fingerprint
from datp_core.config.fingerprinting.projection import unstructure_projection
from datp_core.config.project import resolve_project_configuration
from datp_core.core.numbers import PositiveInt
from datp_core.learning.contracts.model import DenseAutoencoderProfile


def _model(hidden: tuple[int, ...]) -> DenseAutoencoderProfile:
    return DenseAutoencoderProfile(
        identifier="fixed_autoencoder",
        kind="dense_autoencoder",
        hidden_dimensions=tuple(PositiveInt(d) for d in hidden),
        activation="relu",
        output_activation="identity",
        normalization="none",
        use_bias=True,
        objective="mean_squared_error",
        reduction="mean",
        precision="float32",
        weight_initialization="kaiming_uniform",
        bias_initialization="zero",
    )


def test_scientific_fingerprint_changes_when_model_architecture_changes() -> None:
    baseline = compute_fingerprint("scientific", {"model": unstructure_projection(_model((80, 40, 20)))})
    identical = compute_fingerprint("scientific", {"model": unstructure_projection(_model((80, 40, 20)))})
    perturbed = compute_fingerprint("scientific", {"model": unstructure_projection(_model((80, 40, 10)))})
    assert baseline == identical
    assert baseline != perturbed


def test_resolved_scientific_fingerprint_is_deterministic_across_resolutions() -> None:
    first = resolve_project_configuration().scientific_fingerprint
    second = resolve_project_configuration().scientific_fingerprint
    assert first == second
    assert len(first.value) == 64
