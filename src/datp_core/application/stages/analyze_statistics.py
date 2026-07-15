from datp_core.application.ports.statistics import RunStatisticalAnalysisRequest, StatisticalProcedureRunner
from datp_core.domain.artifacts.references import ArtifactReferenceCollection
from datp_core.domain.evaluation.statistical_results import StatisticalAnalysisResult, StatisticalAnalysisSpec


def analyze_statistics(
    *,
    runner: StatisticalProcedureRunner,
    analysis: StatisticalAnalysisSpec,
    input_artifacts: ArtifactReferenceCollection,
) -> StatisticalAnalysisResult:
    return runner.run(RunStatisticalAnalysisRequest(analysis=analysis, input_artifacts=input_artifacts))
