import pytest
from pytest_archon.rule import RuleConstraints, RuleTargets, archrule


@pytest.mark.architecture
def test_domain_imports_only_standard_library_and_domain() -> None:
    rule = archrule(
        "domain imports only the standard library and domain",
        "the domain layer must never import another layer or a scientific framework",
    )
    targets = RuleTargets(rule).match("datp_core.domain*")
    RuleConstraints(rule, targets).should_not_import(
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
