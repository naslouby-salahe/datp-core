from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.core.identifiers import FileContentText
from datp_core.runtime.filesystem import write_text_atomically


class PriorArtCategory(StrEnum):
    YES = "YES"
    NO = "NO"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_REPORTED = "NOT_REPORTED"


@dataclass(frozen=True, slots=True)
class PriorArtDistinctionRow:
    work: str
    source: str
    calibration_object: str
    categories: tuple[PriorArtCategory, ...]
    distinction: str

    def __post_init__(self) -> None:
        if len(self.categories) != 10:
            raise ValueError("prior-art rows require the ten locked categorical fields")


_NOT_REPORTED = tuple(PriorArtCategory.NOT_REPORTED for _ in range(10))
_ROWS = (
    PriorArtDistinctionRow(
        "FedIoT/FedDetect 2021",
        "arXiv:2106.07976",
        "anomaly-score threshold",
        _NOT_REPORTED,
        "controlled fixed-score threshold scope",
    ),
    PriorArtDistinctionRow(
        "Rey et al. 2022",
        "DOI:10.1016/j.comnet.2021.108693",
        "anomaly threshold",
        _NOT_REPORTED,
        "cross-client FPR-dispersion endpoint",
    ),
    PriorArtDistinctionRow(
        "Ochiai et al. 2023",
        "DOI:10.1145/3565287.3616528",
        "coordinated anomaly threshold",
        _NOT_REPORTED,
        "immutable-score causal comparison",
    ),
    PriorArtDistinctionRow(
        "Laridi et al. 2024",
        "roadmap primary source",
        "global threshold selection",
        _NOT_REPORTED,
        "benign-only scope intervention",
    ),
    PriorArtDistinctionRow(
        "FedCal 2024",
        "PMLR:235",
        "predictive-probability calibration",
        _NOT_REPORTED,
        "anomaly operating-point calibration",
    ),
    PriorArtDistinctionRow(
        "Rob-FCP 2024",
        "PMLR:235",
        "Byzantine-robust conformal calibration",
        _NOT_REPORTED,
        "honest-calibration threat boundary",
    ),
    PriorArtDistinctionRow(
        "Asiri et al. 2025",
        "DOI:10.3390/fi17100475",
        "benign p95 threshold",
        _NOT_REPORTED,
        "fixed-detector equity study",
    ),
    PriorArtDistinctionRow(
        "PFCP 2025",
        "NeurIPS 2025",
        "personalized conformal prediction",
        _NOT_REPORTED,
        "bounded supportive conformal diagnostic",
    ),
    PriorArtDistinctionRow(
        "Fed-DTCN 2026",
        "DOI:10.3390/s26061918",
        "client-specific anomaly threshold",
        _NOT_REPORTED,
        "shared frozen-detector evidence",
    ),
    PriorArtDistinctionRow(
        "CF-HFC 2026",
        "arXiv:2602.12557",
        "adaptive conformal calibration",
        _NOT_REPORTED,
        "no multi-component reproduction",
    ),
    PriorArtDistinctionRow(
        "PRISM-FCP 2026",
        "arXiv:2602.18396",
        "Byzantine-robust conformal calibration",
        _NOT_REPORTED,
        "honest-calibration boundary",
    ),
    PriorArtDistinctionRow(
        "Shahid federated CRC 2026",
        "arXiv:2606.20115",
        "site-conditional risk calibration",
        _NOT_REPORTED,
        "IoT anomaly-score operating-point equity",
    ),
    PriorArtDistinctionRow(
        "DATP-Core",
        "this repository",
        "benign anomaly-score threshold",
        (
            PriorArtCategory.YES,
            PriorArtCategory.NO,
            PriorArtCategory.YES,
            PriorArtCategory.NO,
            PriorArtCategory.YES,
            PriorArtCategory.YES,
            PriorArtCategory.PARTIAL,
            PriorArtCategory.YES,
            PriorArtCategory.NO,
            PriorArtCategory.NO,
        ),
        "controlled scope intervention on fixed score artifacts",
    ),
)


def render_prior_art_distinction_table() -> str:
    headings = (
        "Work",
        "Primary calibration object",
        "Detector fixed?",
        "Mapping modified?",
        "Benign-only fitting?",
        "Labels used?",
        "Shared point?",
        "Local point?",
        "Group point?",
        "Same population?",
        "FPR dispersion?",
        "Formal guarantee?",
        "Byzantine guarantee?",
        "DATP-Core distinction",
    )
    lines = [
        "# Source-grounded prior-art distinction table",
        "",
        "| " + " | ".join(headings) + " |",
        "|" + " --- |" * len(headings),
    ]
    lines.extend(
        "| "
        + " | ".join((row.work, row.calibration_object, *(item.value for item in row.categories), row.distinction))
        + " |"
        for row in _ROWS
    )
    lines.extend(("", "Sources: " + "; ".join(f"{row.work} ({row.source})" for row in _ROWS) + "."))
    return "\n".join(lines) + "\n"


def export_prior_art_distinction_table(destination: Path) -> Path:
    return write_text_atomically(destination, FileContentText(render_prior_art_distinction_table()))
