import pytest
from pytest_archon import archrule


@pytest.mark.architecture
def test_domain_imports_only_standard_library_and_domain() -> None:
    # pytest_archon ships an untyped `**kwargs` on `match`/`should_not_import`; the two
    # `reportUnknownMemberType` suppressions below are that third-party stub gap, not ours.
    rule = archrule(
        "domain imports only the standard library and domain",
        "the domain layer must never import another layer or a scientific framework",
    ).match("datp_core.domain*")  # pyright: ignore[reportUnknownMemberType]
    rule.should_not_import(  # pyright: ignore[reportUnknownMemberType]
        "datp_core.application*",
        "datp_core.config*",
        "datp_core.analysis*",
        "datp_core.infrastructure*",
        "datp_core.composition*",
        "datp_core.cli*",
        "torch*",
        "flwr*",
        "sklearn*",
        "scipy*",
        "pandas*",
        "numpy*",
        "pydantic*",
    ).check("datp_core")
