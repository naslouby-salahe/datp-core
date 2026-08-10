from dataclasses import dataclass
from pathlib import Path

from datp_core.app.contracts import ArtifactPresence, ProgrammeExecutionMode, RecipeRegistration
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    NonEmptyString,
    ProgrammeStatus,
    ThresholdMethodExecutionStatus,
)
from datp_core.core.numeric import Seed
from datp_core.experiments.anchor.contracts import AnchorGateStatus


class DetailText(NonEmptyString):
    validation_name = "research detail text"


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdMethodOutcome:
    method: FederatedThresholdMethod
    status: ThresholdMethodExecutionStatus
    detail: DetailText


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchOutcome:
    detail: DetailText
    method_outcomes: tuple[ThresholdMethodOutcome, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRunResult:
    experiment: ExperimentId
    seeds: tuple[Seed, ...]
    mode: ProgrammeExecutionMode
    output_root: Path
    detail: DetailText
    method_outcomes: tuple[ThresholdMethodOutcome, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignRunResult:
    experiments: tuple[ExperimentRunResult, ...]
    detail: DetailText
    anchor_failure: DetailText | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportResult:
    experiment: ExperimentId | None
    paths: tuple[Path, ...]
    detail: DetailText


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentStatusRecord:
    experiment: ExperimentId
    status: ProgrammeStatus
    role: EvidenceRole
    readiness: ExperimentReadiness
    registration: RecipeRegistration
    detail: DetailText


@dataclass(frozen=True, slots=True, kw_only=True)
class ProgrammeStatusReport:
    records: tuple[ExperimentStatusRecord, ...]
    anchor_gate: AnchorGateStatus
    campaign_completion: ArtifactPresence


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCommandResult:
    gate_status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    detail: DetailText
