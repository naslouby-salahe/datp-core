"""Typed analysis requests, documents, and publication records."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.contrasts import PairedContrast, PairedDifferenceCounts, SupplementaryPairedAnalysisPlan
from datp_core.analysis.descriptive import DescriptiveSummary
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.multiplicity import MultiplicityPlan, MultiplicityResult
from datp_core.analysis.inference.wilcoxon import RankBiserialResult, WilcoxonResult
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.scientific_decision import ScientificDecisionResult
from datp_core.analysis.temporal import TemporalAnalysisRecord, TemporalRecoveryResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.statistics import PairedInferenceProtocol
from datp_core.protocols.temporal import TemporalDeploymentProvenance


class AnalysisAssetName(StrEnum):
    DOCUMENT = "analysis.json"
    COMPLETE = "COMPLETE"
    EXTERNAL_DOCUMENT = "external_analysis.json"
    TEMPORAL_DOCUMENT = "temporal_analysis.json"


@dataclass(frozen=True, slots=True)
class ConfirmatoryAnalysisRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
    multiplicity_plan: MultiplicityPlan | None = None
    mechanisms: tuple[MechanismEvidence, ...] = ()


class AnalysisDocument(StrictModel):
    inference_protocol: PairedInferenceProtocol
    interval: BootstrapInterval
    decision: ScientificDecisionResult
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    multiplicity_plan: MultiplicityPlan | None
    multiplicity_result: MultiplicityResult | None
    mechanisms: tuple[MechanismEvidence, ...]

    @model_validator(mode="after")
    def validate_multiplicity(self) -> "AnalysisDocument":
        if (self.multiplicity_plan is None) != (self.multiplicity_result is None):
            raise ValueError("multiplicity plan and result must occur together")
        return self


@dataclass(frozen=True, slots=True)
class ExternalAnalysisRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed


class ExternalAnalysisDocument(StrictModel):
    plan: SupplementaryPairedAnalysisPlan
    interval: BootstrapInterval
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult


@dataclass(frozen=True, slots=True)
class TemporalAnalysisRequest:
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]


class TemporalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalAnalysisRecord, ...]

    @model_validator(mode="after")
    def validate_role_and_records(self) -> "TemporalAnalysisDocument":
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal analysis must remain temporal-boundary evidence")
        if not self.records:
            raise ValueError("temporal analysis requires at least one recovery record")
        seeds = tuple(record.recovery.seed for record in self.records)
        if len(seeds) != len(frozenset(seeds)):
            raise ValueError("temporal recovery records must be unique by seed")
        return self


@dataclass(frozen=True, slots=True)
class AnalysisPublication[DocumentT]:
    asset_name: AnalysisAssetName
    document: DocumentT
    digest: Checksum
