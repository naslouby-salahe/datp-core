"""PNG/PDF figure rendering from a frozen result manifest."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from io import BytesIO

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from datp_core.reporting.freezing import ResultFreezeError


def render_figure(profile: Mapping[str, object], results: list[Mapping[str, object]]) -> dict[str, object]:
    series = _records(profile, "series")
    figure, axis = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    plotted = False
    for result in results:
        values = result.get("seed_differences")
        if isinstance(values, list) and all(isinstance(value, int | float) for value in values):
            axis.plot(range(1, len(values) + 1), values, marker="o", label=str(result["analysis_label"]))
            plotted = True
    if plotted:
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.set_xlabel("Training seed order")
        axis.set_ylabel("Paired difference")
        axis.legend()
    else:
        names = ", ".join(str(item["name"]) for item in series)
        axis.text(0.5, 0.5, f"Unavailable\n{names}", ha="center", va="center")
        axis.set_axis_off()
    axis.set_title(str(profile["identifier"]))
    png = _save_figure(figure, "png")
    pdf = _save_figure(figure, "pdf")
    plt.close(figure)
    return {
        "profile_id": profile["identifier"],
        "artifact_type": "figure",
        "figure_type": profile["figure_type"],
        "outputs": {
            "png_base64": base64.b64encode(png).decode("ascii"),
            "pdf_base64": base64.b64encode(pdf).decode("ascii"),
        },
    }


def _save_figure(figure: Figure, output_format: str) -> bytes:
    output = BytesIO()
    figure.savefig(output, format=output_format, dpi=144, metadata={"Creator": "datp-core"})
    return output.getvalue()


def _records(profile: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    values = profile[key]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError(f"Report profile has malformed {key}")
    return values


__all__ = ["render_figure"]
