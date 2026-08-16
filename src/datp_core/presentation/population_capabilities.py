from dataclasses import dataclass
from pathlib import Path

from datp_core.core.identifiers import FileContentText, PopulationId
from datp_core.runtime.filesystem import write_text_atomically


@dataclass(frozen=True, slots=True)
class PopulationCapabilityTableRow:
    population: PopulationId
    client_identity: str
    locked_client_count: int
    physical_device_claim: str
    fpr_equity_metrics: str
    per_client_attack_metrics: str
    genuine_chronology: str
    evidence_role: str


_ROWS = (
    PopulationCapabilityTableRow(
        PopulationId.NBAIOT_NATURAL_DEVICES,
        "original commercial IoT device",
        9,
        "Yes (small client population)",
        "Yes",
        "Yes, subject to held-out family support",
        "No genuine-time claim from source-row ordering",
        "sole confirmatory + principal mechanism",
    ),
    PopulationCapabilityTableRow(
        PopulationId.CICIOT_FILE_CLIENTS,
        "processed CSV file pseudo-client",
        63,
        "No",
        "Yes",
        "Not authorized for DATP claims",
        "No",
        "applicability boundary",
    ),
    PopulationCapabilityTableRow(
        PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        "synthetic Dirichlet client",
        20,
        "No",
        "Yes",
        "Yes, where source attack support remains valid",
        "No",
        "controlled heterogeneity sensitivity",
    ),
    PopulationCapabilityTableRow(
        PopulationId.EDGE_SENSOR_CLIENTS,
        "benign sensor-group folder",
        10,
        "No physical-device claim",
        "Yes",
        "No — valid per-client attack assignment unavailable",
        "No",
        "independent external benign-equity validation",
    ),
    PopulationCapabilityTableRow(
        PopulationId.EDGE_TEMPORAL_CLIENTS,
        "timestamp-valid sensor-group folder",
        9,
        "No physical-device claim",
        "Yes",
        "No — temporal experiment is benign-only",
        "Yes",
        "one-shot temporal boundary",
    ),
)


def render_population_capability_table() -> str:
    lines = [
        "# Population capability and claim-boundary table",
        "",
        "| Population | Client identity | Locked client count | Natural physical-device claim valid? | "
        "FPR-equity metrics | Per-client attack metrics | Genuine chronology | Primary evidence role |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| `{row.population.value}` | {row.client_identity} | {row.locked_client_count} | "
        f"{row.physical_device_claim} | {row.fpr_equity_metrics} | {row.per_client_attack_metrics} | "
        f"{row.genuine_chronology} | {row.evidence_role} |"
        for row in _ROWS
    )
    lines.extend(("", "Availability of a metric does not itself authorize every scientific claim or threshold method."))
    return "\n".join(lines) + "\n"


def export_population_capability_table(destination: Path) -> Path:
    return write_text_atomically(destination, FileContentText(render_population_capability_table()))
