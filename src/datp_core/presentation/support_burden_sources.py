from dataclasses import dataclass
from math import log10
from pathlib import Path

from datp_core.analysis.mechanisms.support_burden import CalibrationSupportBurdenSeedEvidence
from datp_core.core.identifiers import FileContentText
from datp_core.runtime.filesystem import write_text_atomically

SUPPORT_BURDEN_FPR_SOURCE_FILENAME = "support_vs_shared_fpr.csv"
SUPPORT_BURDEN_RELIEF_SOURCE_FILENAME = "support_vs_personalization_relief.csv"


def export_support_burden_scatter_sources(
    evidence: tuple[CalibrationSupportBurdenSeedEvidence, ...], output_directory: Path
) -> tuple[Path, Path]:
    rows = tuple(
        SupportBurdenScatterRow(
            seed=seed.seed.value,
            client=item.client.client_id.value,
            source_benign_calibration_count=item.source_benign_calibration_count.value,
            log10_source_benign_calibration_count=log10(item.source_benign_calibration_count.value),
            shared_false_positive_rate=item.shared_false_positive_rate.value,
            personalization_relief=item.personalization_relief.value,
        )
        for seed in evidence
        for item in seed.clients
    )
    if not rows:
        raise ValueError("support-burden scatter sources require client seed evidence")
    output_directory.mkdir(parents=True, exist_ok=True)
    fpr_path = output_directory / SUPPORT_BURDEN_FPR_SOURCE_FILENAME
    relief_path = output_directory / SUPPORT_BURDEN_RELIEF_SOURCE_FILENAME
    write_text_atomically(fpr_path, FileContentText(_csv(rows, "shared_false_positive_rate")))
    write_text_atomically(relief_path, FileContentText(_csv(rows, "personalization_relief")))
    return fpr_path, relief_path


@dataclass(frozen=True, slots=True)
class SupportBurdenScatterRow:
    seed: int
    client: str
    source_benign_calibration_count: int
    log10_source_benign_calibration_count: float
    shared_false_positive_rate: float
    personalization_relief: float


def _csv(rows: tuple[SupportBurdenScatterRow, ...], y_label: str) -> str:
    header = f"seed,client,source_benign_calibration_count,log10_source_benign_calibration_count,{y_label}\n"
    values = "".join(
        f"{row.seed},{row.client},{row.source_benign_calibration_count},"
        f"{row.log10_source_benign_calibration_count:.17g},"
        f"{_y_value(row, y_label):.17g}\n"
        for row in rows
    )
    return header + values


def _y_value(row: SupportBurdenScatterRow, y_label: str) -> float:
    return row.shared_false_positive_rate if y_label == "shared_false_positive_rate" else row.personalization_relief
