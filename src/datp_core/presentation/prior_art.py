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
        if len(self.categories) != 11:
            raise ValueError("prior-art rows require the eleven locked categorical fields")


@dataclass(frozen=True, slots=True)
class PriorArtCollisionRow:
    work: str
    overlap: str
    prohibited_claim: str
    distinction: str


_COLLISIONS = (
    PriorArtCollisionRow(
        "Meidan et al. 2018",
        "per-device N-BaIoT AE threshold",
        "first device-specific threshold",
        "fixed federated detector and score artifact",
    ),
    PriorArtCollisionRow(
        "FedIoT 2021",
        "federated AE post-training thresholds",
        "first federated IoT post-training threshold",
        "scope intervention and FPR dispersion endpoint",
    ),
    PriorArtCollisionRow(
        "Rey et al. 2022",
        "server aggregation of local AE thresholds",
        "first threshold aggregation",
        "immutable-score scope comparison",
    ),
    PriorArtCollisionRow(
        "Ochiai et al. 2023",
        "coordinated IoT thresholding",
        "first distributed coordination",
        "scope-only causal comparison",
    ),
    PriorArtCollisionRow(
        "Laridi et al. 2024",
        "federated global threshold selection",
        "first federated threshold-selection study",
        "benign-only scope rather than estimator competition",
    ),
    PriorArtCollisionRow(
        "Komadina et al. 2024",
        "broad threshold-estimator catalogue",
        "first/exhaustive estimator benchmark",
        "fixed q95 estimator in confirmatory ladder",
    ),
    PriorArtCollisionRow(
        "FedCal 2024",
        "local/global FL calibration",
        "first local/global calibration",
        "anomaly-score operating thresholds, not probabilities",
    ),
    PriorArtCollisionRow(
        "Asiri et al. 2025",
        "benign local p95 FL-IoT threshold",
        "first benign p95 client threshold",
        "fixed-detector operating-point equity",
    ),
    PriorArtCollisionRow(
        "Personalized FCP 2025",
        "personalized federated calibration",
        "novel federated conformal calibration",
        "bounded supportive AE diagnostic",
    ),
    PriorArtCollisionRow(
        "G-PFL-ID 2026",
        "personalized unsupervised IoT IDS",
        "first personalized N-BaIoT detector",
        "does not compete on architecture",
    ),
    PriorArtCollisionRow(
        "Fed-DTCN 2026",
        "client-specific threshold",
        "first client-specific federated anomaly threshold",
        "frozen-detector evidence separated from personalization",
    ),
    PriorArtCollisionRow(
        "FBID 2026", "adaptive personalized FL-IDS", "first PFL/OOD IoT IDS", "locked Ditto absorption counterfactual"
    ),
    PriorArtCollisionRow(
        "Robalino-Díaz et al. 2026",
        "AUC versus deployed recall divergence",
        "first discrimination/operation divergence",
        "scope is the controlled intervention",
    ),
    PriorArtCollisionRow(
        "FedWQ-CP 2026",
        "weighted global quantile aggregation",
        "novel federated quantile aggregation",
        "shared constructions are comparators",
    ),
    PriorArtCollisionRow(
        "GC-FCP 2026",
        "group-conditional federated calibration",
        "first group-conditional calibration",
        "no conformal guarantee claim",
    ),
    PriorArtCollisionRow(
        "PFWCP 2026",
        "personalized weighted calibration",
        "novel personalized weighted calibration",
        "empirical anomaly-threshold mechanism",
    ),
    PriorArtCollisionRow(
        "Rob-FCP 2024",
        "Byzantine-robust calibration",
        "secure DATP aggregation",
        "honest calibration-participant boundary",
    ),
    PriorArtCollisionRow(
        "CF-HFC 2026",
        "adaptive conformal heterogeneous IoT IDS",
        "first calibrated heterogeneous FL-IDS",
        "does not reproduce joint system changes",
    ),
    PriorArtCollisionRow(
        "PRISM-FCP 2026",
        "Byzantine training and calibration",
        "end-to-end secure calibration",
        "threat-boundary citation",
    ),
    PriorArtCollisionRow(
        "Shahid 2026",
        "pooled/local calibration and n/(n+n0)",
        "novel sample-size shrinkage",
        "n_min=100 fixed prospectively",
    ),
)


_NOT_REPORTED = tuple(PriorArtCategory.NOT_REPORTED for _ in range(11))
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
        "Detector fixed across the work's threshold/calibration comparison?",
        "Score/probability mapping modified by the calibration method?",
        "Benign-only threshold fitting?",
        "Outcome/class/attack labels used to fit the calibration object?",
        "Shared/federation-wide operating point present?",
        "Client-local operating point present?",
        "Group/cluster operating point present?",
        "Same evaluation population used across compared scopes?",
        "Cross-client FPR dispersion reported as an endpoint?",
        "Formal coverage/risk guarantee?",
        "Adversarial/Byzantine calibration guarantee?",
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


def render_prior_art_collision_table() -> str:
    lines = [
        "# Prior-art collision table",
        "",
        "| Prior work | Relevant overlap | What DATP must not claim | DATP distinction |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {row.work} | {row.overlap} | {row.prohibited_claim} | {row.distinction} |" for row in _COLLISIONS)
    lines.extend(
        (
            "",
            "Submission-time novelty gate: `NOT_EXECUTED`; update this table from the required "
            "14-day literature search before submission.",
        )
    )
    return "\n".join(lines) + "\n"


def export_prior_art_collision_table(destination: Path) -> Path:
    return write_text_atomically(destination, FileContentText(render_prior_art_collision_table()))
