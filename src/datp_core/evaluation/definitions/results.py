"""Evaluation result contract record."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EvaluationResultContractRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: tuple[str, ...]
