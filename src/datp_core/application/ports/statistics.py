from dataclasses import dataclass
from typing import Protocol

from datp_core.domain.artifacts.references import ArtifactReferenceCollection
from datp_core.domain.evaluation.statistical_results import StatisticalAnalysisResult, StatisticalAnalysisSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class RunStatisticalAnalysisRequest:
    analysis: StatisticalAnalysisSpec
    input_artifacts: ArtifactReferenceCollection


class StatisticalProcedureRunner(Protocol):
    def run(self, request: RunStatisticalAnalysisRequest) -> StatisticalAnalysisResult: ...
