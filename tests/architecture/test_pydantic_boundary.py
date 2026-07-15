from pathlib import Path

import pytest


@pytest.mark.architecture
def test_pydantic_is_confined_to_the_configuration_schema_boundary() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    schema_root = source_root / "config" / "schemas"
    importers = tuple(path for path in source_root.rglob("*.py") if "pydantic" in path.read_text().lower())

    assert frozenset(importers) == frozenset(
        schema_root / filename for filename in ("artifacts.py", "execution.py", "reporting.py", "scientific.py")
    )
