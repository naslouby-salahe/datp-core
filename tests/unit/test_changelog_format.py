"""Validates CHANGELOG.md format (P0-T11)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "CHANGELOG.md"

DASHBOARD_FIELDS = [
    "Current phase:",
    "Current ticket:",
    "Overall progress:",
    "Completed tickets:",
    "Blocked tickets:",
    "Last completed ticket:",
    "Next ticket:",
    "Last tests run:",
    "Current blocker:",
    "Last update:",
]

STATUS_ENUM = [
    "Not Started",
    "In Progress",
    "Blocked",
    "Done",
    "Skipped",
    "Split",
    "Merged",
    "Reopened",
]

# Experimental-result vocabulary that would turn this tracker into a results
# file. Ticket-status words like "Done"/"passed" are not results claims.
FORBIDDEN_RESULT_TERMS = [
    "CV(FPR) =",
    "AUROC =",
    "p-value",
    "BCa CI [",
    "reduces CV(FPR) from",
]


def test_dashboard_fields_present() -> None:
    text = DOC.read_text()
    dashboard = re.search(r"## 1\. Current Status Dashboard.*?```text(.*?)```", text, flags=re.DOTALL)
    assert dashboard is not None
    body = dashboard.group(1)
    for field in DASHBOARD_FIELDS:
        assert field in body, f"missing dashboard field: {field!r}"


def test_status_enum_values() -> None:
    text = DOC.read_text()
    header = text.split("---", 1)[0]
    for status in STATUS_ENUM:
        assert status in header


def test_update_template_present() -> None:
    text = DOC.read_text()
    template = re.search(r"## 14\. Update Template.*?```text(.*?)```", text, flags=re.DOTALL)
    assert template is not None
    body = template.group(1)
    for field in ["Status:", "Summary:", "Files changed:", "Tests added:", "Tests run:", "Result:", "Next ticket:"]:
        assert field in body


def test_no_experimental_claims_in_changelog() -> None:
    text = DOC.read_text()
    for term in FORBIDDEN_RESULT_TERMS:
        assert term not in text, f"experimental-claim vocabulary found: {term!r}"
    assert "not a scientific result file" in text
