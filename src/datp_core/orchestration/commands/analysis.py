"""Typed analysis commands and stage outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.analysis.decisions import (
    AnalysisDocument,
    ExternalAnalysisDocument,
    TemporalAnalysisDocument,
)
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.models import (
    BootstrapInterval,
    MultiplicityPlan,
    MultiplicityResult,
    PairedContrast,
    PairedDifferenceCounts,
    RankBiserialResult,
    ScientificDecisionResult,
    SupplementaryPairedAnalysisPlan,
    WilcoxonResult,
)
from datp_core.analysis.descriptive import DescriptiveSummary
from datp_core.analysis.temporal import TemporalAnalysisRecord, TemporalDeploymentProvenance, TemporalRecoveryResult
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, Seed
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.protocols.statistics import PairedInferenceProtocol


@dataclass(frozen=True, slots=True)
class AnalyzeRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool
    multiplicity_plan: MultiplicityPlan | None = None
    mechanisms: tuple[MechanismEvidence, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    stage: ClassVar[StageOperationId] = StageOperationId.ANALYZE
    publication_status: PublicationStatus
    document: AnalysisDocument
    complete_digest: Checksum

    @property
    def interval(self) -> BootstrapInterval:
        return self.document.interval

    @property
    def decision(self) -> ScientificDecisionResult:
        return self.document.decision

    @property
    def descriptive(self) -> DescriptiveSummary:
        return self.document.descriptive

    @property
    def sign_consistency(self) -> PairedDifferenceCounts:
        return self.document.sign_consistency

    @property
    def wilcoxon(self) -> WilcoxonResult:
        return self.document.wilcoxon

    @property
    def rank_biserial(self) -> RankBiserialResult:
        return self.document.rank_biserial

    @property
    def multiplicity(self) -> MultiplicityResult | None:
        return self.document.multiplicity_result

    @property
    def mechanisms(self) -> tuple[MechanismEvidence, ...]:
        return self.document.mechanisms


@dataclass(frozen=True, slots=True)
class ExternalAnalyzeRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ExternalAnalyzeResult:
    stage: ClassVar[StageOperationId] = StageOperationId.ANALYZE
    publication_status: PublicationStatus
    document: ExternalAnalysisDocument
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class TemporalAnalyzeRequest:
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TemporalAnalyzeResult:
    stage: ClassVar[StageOperationId] = StageOperationId.ANALYZE
    publication_status: PublicationStatus
    document: TemporalAnalysisDocument
    complete_digest: Checksum

    @property
    def records(self) -> tuple[TemporalAnalysisRecord, ...]:
        return self.document.records
