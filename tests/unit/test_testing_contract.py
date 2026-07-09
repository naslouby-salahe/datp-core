"""Validates docs/protocol/testing_contract.md (P0-T08)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "testing_contract.md"

REQUIRED_SECTIONS = [
    "## 1. Unit Tests",
    "## 2. Integration Tests",
    "## 3. Smoke / E2E Tests",
    "## 4. Negative / Failure-Mode Tests",
]

GENERIC_PLACEHOLDERS = ["add tests", "TODO", "TBD tests", "write tests later"]


def test_every_subsystem_has_named_tests() -> None:
    text = DOC.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in text
    unit_section = re.search(r"## 1\. Unit Tests.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert unit_section is not None
    subsystem_rows = re.findall(r"^\| ([^|]+) \| ([^|]+) \| [^|]+ \|", unit_section.group(0), flags=re.MULTILINE)
    subsystem_rows = [r for r in subsystem_rows if r[0].strip() not in ("Subsystem",)]
    assert len(subsystem_rows) >= 20
    for row in subsystem_rows:
        assert row[1].strip() != "", "unit-test row missing an owning ticket"


def test_no_generic_add_tests_placeholder() -> None:
    text = DOC.read_text()
    body = text.split("## 1. Unit Tests", 1)[1].lower()
    for placeholder in GENERIC_PLACEHOLDERS:
        assert placeholder.lower() not in body
