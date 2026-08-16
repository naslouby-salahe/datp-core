from enum import StrEnum

from datp_core.runtime.configuration import OUTPUTS_ROOT, RESULTS_ROOT


class ResearchDirectory(StrEnum):
    SMOKE = "smoke"
    SUMMARY = "summary"
    ANCHOR = "anchor"
    DIAGNOSTICS = "diagnostics"
    CAMPAIGN = "campaign"
    CENTRALIZED_REFERENCE = "centralized_reference"
    SUPPLEMENTARY = "supplementary"


class ResearchArtifact(StrEnum):
    SMOKE_SUMMARY = "smoke_summary.txt"
    EVIDENCE_REPORT = "evidence_report.md"
    EXECUTION = "EXECUTION"
    PUBLICATION = "PUBLICATION"
    RESULTS = "results.json"
    RESULTS_TABLE = "results.csv"


class DeliveryDirectory(StrEnum):
    FIGURES = "figures"
    JSON = "json"
    CSV = "csv"
    REPORTS = "reports"


class DeliveryArtifactName(StrEnum):
    MANIFEST = "manifest.json"
    SUMMARY = "summary.json"


SMOKE_OUTPUT_ROOT = OUTPUTS_ROOT / ResearchDirectory.SMOKE
SMOKE_SUMMARY_DIRECTORY = SMOKE_OUTPUT_ROOT / ResearchDirectory.SUMMARY
ANCHOR_DIAGNOSTICS_DIRECTORY = OUTPUTS_ROOT / ResearchDirectory.ANCHOR / ResearchDirectory.DIAGNOSTICS
CAMPAIGN_EXECUTION_MARKER = OUTPUTS_ROOT / ResearchDirectory.CAMPAIGN / ResearchArtifact.EXECUTION
CAMPAIGN_PUBLICATION_MARKER = OUTPUTS_ROOT / ResearchDirectory.CAMPAIGN / ResearchArtifact.PUBLICATION
DELIVERY_RESULTS_ROOT = RESULTS_ROOT
