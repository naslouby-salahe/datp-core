from typing import Protocol

from datp_core.application.ports.scoring import GenerateTemporalScoresRequest, TemporalScoreGenerationResult


class TemporalScoreGenerationWorkflow(Protocol):
    def generate(self, request: GenerateTemporalScoresRequest) -> TemporalScoreGenerationResult: ...
