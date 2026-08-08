"""Typed multiplicity plans and Holm-adjusted decisions."""

from typing import ClassVar

from pydantic import model_validator
from statsmodels.stats.multitest import multipletests

from datp_core.analysis.inference.wilcoxon import PValue, PairedInferenceProtocol
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    MultiplicityCorrectionId,
    NonEmptyString,
)
from datp_core.core.numeric import PositiveIntegerValue, Ratio


class FamilyName(NonEmptyString):
    validation_name: ClassVar[str] = "family name"


class FamilySize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "family size"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value < 2:
            raise ValueError("family size requires at least two tests")


class HypothesisIdentifier(NonEmptyString):
    validation_name: ClassVar[str] = "hypothesis identifier"


class MultiplicityHypothesis(StrictModel):
    hypothesis_id: HypothesisIdentifier
    experiment: ExperimentId
    metric: MetricId
    comparison: str
    left_method: FederatedThresholdMethod | None
    right_method: FederatedThresholdMethod | None
    evidence_role: EvidenceRole
    raw_p_value: PValue

    @model_validator(mode="after")
    def validate_hypothesis(self) -> "MultiplicityHypothesis":
        if not self.comparison.strip():
            raise ValueError("multiplicity hypothesis requires a non-empty comparison label")
        if (self.left_method is None) != (self.right_method is None):
            raise ValueError("multiplicity hypothesis threshold methods must both be present or both absent")
        if self.left_method is not None and self.left_method is self.right_method:
            raise ValueError("multiplicity hypothesis requires distinct threshold methods when present")
        return self


class MultiplicityPlan(StrictModel):
    family_name: FamilyName
    declared_family_size: FamilySize
    hypotheses: tuple[MultiplicityHypothesis, ...]
    alpha: Ratio

    @model_validator(mode="after")
    def validate_plan(self) -> "MultiplicityPlan":
        if len(self.hypotheses) != self.declared_family_size.value:
            raise ValueError("multiplicity family size must equal the number of declared hypotheses")
        identifiers = tuple(item.hypothesis_id for item in self.hypotheses)
        if len(frozenset(identifiers)) != len(identifiers):
            raise ValueError("multiplicity hypothesis identifiers must be unique within a family")
        return self

    @property
    def raw_p_values(self) -> tuple[PValue, ...]:
        return tuple(item.raw_p_value for item in self.hypotheses)


class MultiplicityDecision(StrictModel):
    hypothesis: MultiplicityHypothesis
    adjusted_p_value: PValue
    rejected: bool

    @property
    def raw_p_value(self) -> PValue:
        return self.hypothesis.raw_p_value


class MultiplicityResult(StrictModel):
    correction: MultiplicityCorrectionId
    family_name: FamilyName
    family_size: FamilySize
    decisions: tuple[MultiplicityDecision, ...]

    @model_validator(mode="after")
    def validate_result(self) -> "MultiplicityResult":
        if self.family_size.value != len(self.decisions):
            raise ValueError("multiplicity family size must match the decision count")
        identifiers = tuple(item.hypothesis.hypothesis_id for item in self.decisions)
        if len(frozenset(identifiers)) != len(identifiers):
            raise ValueError("multiplicity decisions must remain uniquely identified")
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


def holm_adjust(plan: MultiplicityPlan, protocol: PairedInferenceProtocol) -> MultiplicityResult:
    if protocol.multiplicity_correction is not MultiplicityCorrectionId.HOLM:
        raise ValueError("DATP paired multiplicity requires the declared Holm correction")
    rejected, adjusted, _, _ = multipletests(
        tuple(value.value for value in plan.raw_p_values),
        alpha=plan.alpha.value,
        method=protocol.multiplicity_correction.value,
        is_sorted=False,
        returnsorted=False,
    )
    decisions = tuple(
        MultiplicityDecision(
            hypothesis=hypothesis,
            adjusted_p_value=PValue(float(corrected)),
            rejected=bool(is_rejected),
        )
        for hypothesis, corrected, is_rejected in zip(
            plan.hypotheses,
            adjusted,
            rejected,
            strict=True,
        )
    )
    return MultiplicityResult(
        correction=protocol.multiplicity_correction,
        family_name=plan.family_name,
        family_size=plan.declared_family_size,
        decisions=decisions,
    )
