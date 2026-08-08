"""Application-owned output layout for campaign, smoke, anchor, and supplementary evidence."""

from enum import StrEnum

from datp_core.runtime.configuration import OUTPUTS_ROOT


class ResearchDirectory(StrEnum):
    SMOKE = "smoke"
    SUMMARY = "summary"
    ANCHOR = "anchor"
    DIAGNOSTICS = "diagnostics"
    CAMPAIGN = "campaign"
    CENTRALIZED_REFERENCE = "centralized_reference"
    SUPPLEMENTARY = "supplementary"


class ResearchArtifact(StrEnum):
    COMPLETE = "COMPLETE"
    EVIDENCE_REPORT = "evidence_report.md"


SMOKE_OUTPUT_ROOT = OUTPUTS_ROOT / ResearchDirectory.SMOKE
SMOKE_SUMMARY_DIRECTORY = SMOKE_OUTPUT_ROOT / ResearchDirectory.SUMMARY
ANCHOR_DIAGNOSTICS_DIRECTORY = OUTPUTS_ROOT / ResearchDirectory.ANCHOR / ResearchDirectory.DIAGNOSTICS
CAMPAIGN_COMPLETION_MARKER = OUTPUTS_ROOT / ResearchDirectory.CAMPAIGN / ResearchArtifact.COMPLETE
CENTRALIZED_REFERENCE_COMPLETION_MARKER = (
    OUTPUTS_ROOT / ResearchDirectory.CENTRALIZED_REFERENCE / ResearchArtifact.COMPLETE
)
