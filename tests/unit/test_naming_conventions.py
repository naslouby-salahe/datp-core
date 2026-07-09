"""Validates docs/protocol/naming_conventions.md (P0-T06)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "naming_conventions.md"

KNOWN_SUITES = {
    "confirmatory_regime_a",
    "regime_c_dirichlet",
    "external_validation_regime_d",
    "threshold_variants",
    "stress_tests",
    "temporal_recalibration",
    "full_journal",
}

EXPECTED_IDS = (
    ["E-C1"]
    + [f"E-S{i}" for i in (1, 2, 3)]
    + [f"E-M{i}" for i in (1, 2, 3, 4, 5)]
    + [f"E-V{i}" for i in (1, 2, 3)]
    + ["E-X1"]
    + [f"E-T{i}" for i in (1, 2, 3)]
    + ["E-B1", "E-O1"]
    + [f"E-Q{i}" for i in range(1, 7)]
)


def _registry_rows() -> list[tuple[str, str]]:
    text = DOC.read_text()
    section = re.search(r"## 3\. Experiment-ID Registry.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert section is not None
    rows = re.findall(r"^\| (E-\w+) \| [^|]+ \| `([a-z_]+)` \|", section.group(0), flags=re.MULTILINE)
    return rows


def test_experiment_ids_unique() -> None:
    rows = _registry_rows()
    ids = [r[0] for r in rows]
    assert sorted(ids) == sorted(EXPECTED_IDS)
    assert len(ids) == len(set(ids))


def test_suite_names_map_to_known_experiments() -> None:
    rows = _registry_rows()
    for exp_id, suite in rows:
        assert suite in KNOWN_SUITES, f"{exp_id} maps to unknown suite {suite!r}"


def test_no_stale_policy_names_in_registry() -> None:
    rows = _registry_rows()
    for exp_id, _ in rows:
        assert exp_id != "B5"
    text = DOC.read_text()
    assert "| B5 |" not in text
    assert "| B3-LGS |" not in text
    assert 'never hardcodes `"Ditto"`' in text
