"""Typed multiplicity plans and Holm-adjusted decisions."""

from pydantic import model_validator
from statsmodels.stats.multitest import multipletests

from datp_core.analysis.inference.wilcoxon import PValue
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import MultiplicityCorrectionId
from datp_core.domain.values import Ratio
from datp_core.protocols.statistics import PairedInferenceProtocol


class MultiplicityPlan(StrictModel):
    family_name: str
    raw_p_values: tuple[PValue, ...]
    alpha: Ratio

    @model_validator(mode="after")
    def validate_plan(self) -> "MultiplicityPlan":
        if not self.family_name.strip() or not self.raw_p_values:
            raise ValueError("multiplicity requires a named non-empty test family")
        return self


class MultiplicityDecision(StrictModel):
    raw_p_value: PValue
    adjusted_p_value: PValue
    rejected: bool


class MultiplicityResult(StrictModel):
    correction: MultiplicityCorrectionId
    family_name: str
    decisions: tuple[MultiplicityDecision, ...]

    @model_validator(mode="after")
    def validate_result(self) -> "MultiplicityResult":
        if not self.family_name.strip() or not self.decisions:
            raise ValueError("multiplicity result requires a named non-empty family")
        return self

    @property
    def raw_p_values(self) -> tuple[PValue, ...]:
        return tuple(item.raw_p_value for item in self.decisions)

    @property
    def adjusted_p_values(self) -> tuple[PValue, ...]:
        return tuple(item.adjusted_p_value for item in self.decisions)

    @property
    def rejected(self) -> tuple[bool, ...]:
        return tuple(item.rejected for item in self.decisions)


def holm_adjust(
    plan: MultiplicityPlan,
    protocol: PairedInferenceProtocol,
) -> MultiplicityResult:
    rejected, adjusted, _, _ = multipletests(
        tuple(value.value for value in plan.raw_p_values),
        alpha=plan.alpha.value,
        method=protocol.multiplicity_correction.value,
        is_sorted=False,
        returnsorted=False,
    )
    return MultiplicityResult(
        correction=protocol.multiplicity_correction,
        family_name=plan.family_name,
        decisions=tuple(
            MultiplicityDecision(
                raw_p_value=raw,
                adjusted_p_value=PValue(float(corrected)),
                rejected=bool(is_rejected),
            )
            for raw, corrected, is_rejected in zip(
                plan.raw_p_values,
                adjusted,
                rejected,
                strict=True,
            )
        ),
    )
