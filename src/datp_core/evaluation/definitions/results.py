"""Evaluation result contract record."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class EvaluationResultContractRecord:
    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: tuple[str, ...]
