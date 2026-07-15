from typing import Protocol

from datp_core.application.ports.scoring import GenerateTestScoresRequest, TestScoreGenerationResult


class TestScoreGenerationWorkflow(Protocol):
    def generate(self, request: GenerateTestScoresRequest) -> TestScoreGenerationResult: ...
