import pytest

from datp_core.analysis.contrasts import (
    ConfirmatoryDescriptiveEffect,
    ConfirmatoryDescriptiveEffects,
)
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.confirmatory import run
from datp_core.presentation.export import _render_confirmatory_descriptive_effects


def test_relative_cv_reduction_uses_the_locked_paired_formula() -> None:
    effect = ConfirmatoryDescriptiveEffect(
        seed=Seed(0),
        shared_cv_fpr=MetricValue(0.4),
        local_cv_fpr=MetricValue(0.1),
        relative_cv_reduction=MetricValue(0.75),
        delta_worst_fpr=MetricValue(0.02),
        delta_iqr_fpr=MetricValue(0.01),
    )

    assert effect.relative_cv_reduction == MetricValue(0.75)


def test_relative_cv_reduction_is_unavailable_at_the_locked_near_zero_cutoff() -> None:
    effect = ConfirmatoryDescriptiveEffect(
        seed=Seed(0),
        shared_cv_fpr=MetricValue(1e-12),
        local_cv_fpr=MetricValue(0.0),
        relative_cv_reduction=None,
        delta_worst_fpr=MetricValue(0.0),
        delta_iqr_fpr=MetricValue(0.0),
    )

    assert effect.relative_cv_reduction is None


def test_descriptive_effects_require_seed_order() -> None:
    effect = ConfirmatoryDescriptiveEffect(
        seed=Seed(1),
        shared_cv_fpr=MetricValue(0.4),
        local_cv_fpr=MetricValue(0.1),
        relative_cv_reduction=MetricValue(0.75),
        delta_worst_fpr=MetricValue(0.02),
        delta_iqr_fpr=MetricValue(0.01),
    )
    earlier = effect.model_copy(update={"seed": Seed(0)})

    with pytest.raises(ValueError, match="ordered"):
        ConfirmatoryDescriptiveEffects(values=(effect, earlier))


def test_descriptive_effect_rendering_includes_percentage() -> None:
    effect = ConfirmatoryDescriptiveEffect(
        seed=Seed(0),
        shared_cv_fpr=MetricValue(0.4),
        local_cv_fpr=MetricValue(0.1),
        relative_cv_reduction=MetricValue(0.75),
        delta_worst_fpr=MetricValue(0.02),
        delta_iqr_fpr=MetricValue(0.01),
    )

    rendered = "\n".join(_render_confirmatory_descriptive_effects(ConfirmatoryDescriptiveEffects(values=(effect,))))

    assert "Relative CV reduction (%)" in rendered
    assert "75.000%" in rendered


def test_confirmatory_descriptive_effects_preserve_worst_fpr_and_iqr_deltas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_document = object()
    local_document = object()
    values = {
        (shared_document, MetricId.FPR_COEFFICIENT_OF_VARIATION): MetricValue(0.4),
        (local_document, MetricId.FPR_COEFFICIENT_OF_VARIATION): MetricValue(0.1),
        (shared_document, MetricId.WORST_CLIENT_FPR): MetricValue(0.7),
        (local_document, MetricId.WORST_CLIENT_FPR): MetricValue(0.2),
        (shared_document, MetricId.FPR_IQR): MetricValue(0.3),
        (local_document, MetricId.FPR_IQR): MetricValue(0.05),
    }
    paths = {
        FederatedThresholdMethod.SHARED_THRESHOLD: shared_document,
        FederatedThresholdMethod.LOCAL_THRESHOLD: local_document,
    }
    monkeypatch.setattr(run, "CONFIRMATORY_SEED_COHORT", SeedCohort(values=(Seed(0),)))
    monkeypatch.setattr(run, "_evaluation_path", lambda _seed, method: method)
    monkeypatch.setattr(run, "load_evaluation_document", lambda method: paths[method])
    monkeypatch.setattr(run, "population_metric", lambda document, metric: values[(document, metric)])

    effect = run._confirmatory_descriptive_effects().values[0]

    assert effect.delta_worst_fpr.value == pytest.approx(0.5)
    assert effect.delta_iqr_fpr.value == pytest.approx(0.25)
