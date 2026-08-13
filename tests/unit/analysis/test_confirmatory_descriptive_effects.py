import pytest

from datp_core.analysis.contrasts import (
    ConfirmatoryDescriptiveEffect,
    ConfirmatoryDescriptiveEffects,
)
from datp_core.core.numeric import MetricValue, Seed
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
