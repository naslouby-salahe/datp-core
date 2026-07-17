from dataclasses import dataclass

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, PartitionIdentity
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.statistical_results import (
    AnchorReproductionResult,
    CoverageRatio,
    FailedAnchorReproductionResult,
    PassedAnchorReproductionResult,
)
from datp_core.domain.experiments.feasibility import BlockingReason, ScientificReadinessResult
from datp_core.domain.experiments.specifications import RegimeDViabilityGateSpec


class ScientificReadinessEvaluator:
    def evaluate(self, *, blockers: tuple[BlockingReason, ...]) -> ScientificReadinessResult:
        return ScientificReadinessResult(blockers=blockers)


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorReproductionGateRequest:
    result: AnchorReproductionResult

    def __post_init__(self) -> None:
        if type(self.result) not in (PassedAnchorReproductionResult, FailedAnchorReproductionResult):
            raise DomainValidationError(
                detail="anchor reproduction gate requires a typed reproduction result",
                value=repr(self.result),
                constraint="PassedAnchorReproductionResult or FailedAnchorReproductionResult",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorGateDecision:
    readiness: ScientificReadinessResult


class AnchorReproductionGate:
    def evaluate(self, request: AnchorReproductionGateRequest) -> AnchorGateDecision:
        if isinstance(request.result, FailedAnchorReproductionResult):
            return AnchorGateDecision(
                readiness=ScientificReadinessResult(blockers=(BlockingReason.FAILED_ANCHOR_GATE,))
            )
        return AnchorGateDecision(readiness=ScientificReadinessResult(blockers=()))

    def require_journal_expansion(self, request: AnchorReproductionGateRequest) -> None:
        if isinstance(request.result, FailedAnchorReproductionResult):
            raise request.result.failure


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeDFeasibilityEvidence:
    audited_source_identity: DatasetSourceIdentity
    audited_partition_identity: PartitionIdentity
    requested_source_identity: DatasetSourceIdentity
    requested_partition_identity: PartitionIdentity
    eligibility_coverage: CoverageRatio

    def __post_init__(self) -> None:
        if (
            type(self.audited_source_identity) is not DatasetSourceIdentity
            or type(self.audited_partition_identity) is not PartitionIdentity
            or type(self.requested_source_identity) is not DatasetSourceIdentity
            or type(self.requested_partition_identity) is not PartitionIdentity
            or type(self.eligibility_coverage) is not CoverageRatio
        ):
            raise DomainValidationError(
                detail="Regime D feasibility requires exact typed source, partition, and coverage evidence",
                value=repr(self),
                constraint="typed source/partition identities and CoverageRatio",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FeasibilityGateDecision:
    readiness: ScientificReadinessResult
    eligibility_coverage: CoverageRatio


@dataclass(frozen=True, slots=True, kw_only=True)
class FeasibilityGateRequest:
    evidence: RegimeDFeasibilityEvidence

    def __post_init__(self) -> None:
        if type(self.evidence) is not RegimeDFeasibilityEvidence:
            raise DomainValidationError(
                detail="feasibility gate requires typed Regime D evidence",
                value=repr(self.evidence),
                constraint="RegimeDFeasibilityEvidence",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FeasibilityGateEvaluator:
    viability: RegimeDViabilityGateSpec

    def __post_init__(self) -> None:
        if type(self.viability) is not RegimeDViabilityGateSpec:
            raise DomainValidationError(
                detail="feasibility gate requires a typed Regime D viability specification",
                value=repr(self.viability),
                constraint="RegimeDViabilityGateSpec",
            )

    def evaluate(self, request: FeasibilityGateRequest) -> FeasibilityGateDecision:
        evidence = request.evidence
        blockers: list[BlockingReason] = []
        if evidence.audited_source_identity != evidence.requested_source_identity or (
            evidence.audited_partition_identity != evidence.requested_partition_identity
        ):
            blockers.append(BlockingReason.INVALID_LINEAGE)
        if evidence.eligibility_coverage.value < self.viability.minimum_eligibility_coverage.value:
            blockers.append(BlockingReason.FAILED_FEASIBILITY)
        return FeasibilityGateDecision(
            readiness=ScientificReadinessResult(blockers=tuple(blockers)),
            eligibility_coverage=evidence.eligibility_coverage,
        )
