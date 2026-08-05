"""Preflight and final-acceptance validation for pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.pipeline.campaign import CampaignPlan
from datp_core.pipeline.planning import ExperimentPlan


class AcceptanceStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceCheck:
    name: str
    status: AcceptanceStatus
    evidence: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.evidence.strip():
            raise ValueError("acceptance checks require a name and evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceReport:
    checks: tuple[AcceptanceCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.status is AcceptanceStatus.PASSED for check in self.checks)


def validate_preflight(
    *,
    plan: ExperimentPlan,
    campaign: CampaignPlan,
    output_root: Path,
    cuda_available: bool,
    require_cuda: bool,
) -> AcceptanceReport:
    checks = (
        AcceptanceCheck(
            name="plan_digest",
            status=AcceptanceStatus.PASSED,
            evidence=f"validated deterministic plan {plan.digest}",
        ),
        AcceptanceCheck(
            name="campaign_digest",
            status=AcceptanceStatus.PASSED,
            evidence=f"validated deterministic campaign {campaign.digest}",
        ),
        AcceptanceCheck(
            name="output_root",
            status=AcceptanceStatus.PASSED if output_root.parts else AcceptanceStatus.FAILED,
            evidence=str(output_root) if output_root.parts else "output root is empty",
        ),
        AcceptanceCheck(
            name="cuda",
            status=(
                AcceptanceStatus.PASSED
                if cuda_available or not require_cuda
                else AcceptanceStatus.BLOCKED
            ),
            evidence=(
                "CUDA requirement satisfied"
                if cuda_available
                else "CUDA unavailable while the runtime protocol requires CUDA"
            ),
        ),
    )
    return AcceptanceReport(checks=checks)


class ExtensionKind(StrEnum):
    ATTACK = "attack"
    DEFENSE = "defense"
    DATASET = "dataset"
    DYNAMIC_ADAPTATION = "dynamic_adaptation"
    THRESHOLD_METHOD = "threshold_method"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionRequest:
    kind: ExtensionKind
    identity: str

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("extension requests require an identity")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionDecision:
    permitted: bool
    reason: str


def assess_extension(request: ExtensionRequest) -> ExtensionDecision:
    if request.kind in {ExtensionKind.ATTACK, ExtensionKind.DEFENSE}:
        return ExtensionDecision(
            permitted=False,
            reason="attacks and defenses are outside DATP-Core",
        )
    if request.kind is ExtensionKind.DYNAMIC_ADAPTATION:
        return ExtensionDecision(
            permitted=False,
            reason="DATP-Core permits one-shot recalibration only",
        )
    if request.kind is ExtensionKind.DATASET:
        return ExtensionDecision(
            permitted=False,
            reason="DATP-Core adds no dataset beyond Edge-IIoTset",
        )
    return ExtensionDecision(
        permitted=False,
        reason="future extensions require a separately approved scientific protocol",
    )
