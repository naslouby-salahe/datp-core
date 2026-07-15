from dataclasses import dataclass

from datp_core.domain.artifacts.lineage import ReuseDecisionKind
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.feasibility import BlockingReason, ReuseIncompatibilityReason
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    CalibrationScoringLineage,
    TemporalScoreArtifactSet,
    TemporalScoringLineage,
    TestScoreArtifactSet,
    TestScoringLineage,
)

type ReusableScoreArtifactSet = CalibrationScoreArtifactSet | TestScoreArtifactSet | TemporalScoreArtifactSet


@dataclass(frozen=True, slots=True, kw_only=True)
class ReuseArtifactDecision:
    artifact: ReusableScoreArtifactSet
    kind: ReuseDecisionKind = ReuseDecisionKind.REUSE

    def __post_init__(self) -> None:
        if not _has_kind(value=self.kind, expected=ReuseDecisionKind.REUSE):
            raise DomainValidationError(
                detail="a reused score artifact must have the reuse decision kind",
                value=repr(self.kind),
                constraint="ReuseDecisionKind.REUSE",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RecomputeArtifactDecision:
    incompatibility: ReuseIncompatibilityReason | None
    kind: ReuseDecisionKind = ReuseDecisionKind.RECOMPUTE

    def __post_init__(self) -> None:
        if not _has_kind(value=self.kind, expected=ReuseDecisionKind.RECOMPUTE):
            raise DomainValidationError(
                detail="a recompute decision must have the recompute decision kind",
                value=repr(self.kind),
                constraint="ReuseDecisionKind.RECOMPUTE",
            )
        if self.incompatibility is not None and type(self.incompatibility) is not ReuseIncompatibilityReason:
            raise DomainValidationError(
                detail="a recompute decision requires a typed incompatibility reason when a candidate exists",
                value=repr(self.incompatibility),
                constraint="ReuseIncompatibilityReason | None",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class BlockedReuseDecision:
    reason: BlockingReason
    kind: ReuseDecisionKind = ReuseDecisionKind.BLOCKED

    def __post_init__(self) -> None:
        if not _has_kind(value=self.kind, expected=ReuseDecisionKind.BLOCKED):
            raise DomainValidationError(
                detail="a blocked reuse decision must have the blocked decision kind",
                value=repr(self.kind),
                constraint="ReuseDecisionKind.BLOCKED",
            )
        if type(self.reason) is not BlockingReason:
            raise DomainValidationError(
                detail="a blocked reuse decision requires a typed blocking reason",
                value=repr(self.reason),
                constraint="BlockingReason",
            )


type ReuseDecision = ReuseArtifactDecision | RecomputeArtifactDecision | BlockedReuseDecision


def _has_kind(*, value: ReuseDecisionKind, expected: ReuseDecisionKind) -> bool:
    return type(value) is ReuseDecisionKind and value is expected


class ScoreReuseGate:
    def decide_calibration(
        self,
        required: CalibrationScoringLineage,
        candidate: CalibrationScoreArtifactSet | None,
    ) -> ReuseDecision:
        return _decide(required=required, candidate=candidate)

    def decide_test(self, required: TestScoringLineage, candidate: TestScoreArtifactSet | None) -> ReuseDecision:
        return _decide(required=required, candidate=candidate)

    def decide_temporal(
        self,
        required: TemporalScoringLineage,
        candidate: TemporalScoreArtifactSet | None,
    ) -> ReuseDecision:
        return _decide(required=required, candidate=candidate)


type ScoreLineage = CalibrationScoringLineage | TestScoringLineage | TemporalScoringLineage


def _decide(*, required: ScoreLineage, candidate: ReusableScoreArtifactSet | None) -> ReuseDecision:
    if candidate is None:
        return RecomputeArtifactDecision(incompatibility=None)
    incompatibility = _incompatibility(required=required, candidate=candidate)
    if incompatibility is None:
        return ReuseArtifactDecision(artifact=candidate)
    return RecomputeArtifactDecision(incompatibility=incompatibility)


def _incompatibility(
    *,
    required: ScoreLineage,
    candidate: ReusableScoreArtifactSet,
) -> ReuseIncompatibilityReason | None:
    candidate_lineage = candidate.lineage
    if type(required) is not type(candidate_lineage):
        return ReuseIncompatibilityReason.SCORING_MISMATCH
    if required == candidate_lineage:
        return None
    return ReuseIncompatibilityReason.SCORING_MISMATCH
