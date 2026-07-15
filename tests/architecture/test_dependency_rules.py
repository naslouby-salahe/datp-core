import ast
from pathlib import Path

import pytest
from pytest_archon.rule import RuleConstraints, RuleTargets, archrule

SOURCE_ROOT = Path("src/datp_core")


@pytest.mark.architecture
def test_pytest_archon_enforces_each_forbidden_layer_direction() -> None:
    _assert_forbidden_imports(
        "datp_core.domain*",
        "datp_core.application*",
        "datp_core.config*",
        "datp_core.analysis*",
        "datp_core.infrastructure*",
        "datp_core.composition*",
        "datp_core.cli*",
    )


@pytest.mark.architecture
def test_internal_imports_follow_the_complete_layer_diagram() -> None:
    assert not _layer_violations(SOURCE_ROOT)


def test_layer_diagram_rejects_an_adversarial_forbidden_edge(tmp_path: Path) -> None:
    module = tmp_path / "cli" / "bad.py"
    module.parent.mkdir()
    module.write_text("from datp_core.infrastructure import persistence\n")

    assert _layer_violations(tmp_path) == ((module, "datp_core.infrastructure"),)


@pytest.mark.architecture
def test_closed_union_matches_place_assert_never_in_the_terminal_wildcard_case() -> None:
    for path in SOURCE_ROOT.rglob("*.py"):
        for match in _matches(path):
            _assert_match_is_exhaustive(path, match)


def _layer_violations(root: Path) -> tuple[tuple[Path, str], ...]:
    allowed_targets = {
        "domain": frozenset({"domain"}),
        "application": frozenset({"application", "domain", "analysis"}),
        "config": frozenset({"config", "domain"}),
        "analysis": frozenset({"analysis", "domain", "application"}),
        "infrastructure": frozenset({"infrastructure", "application", "domain", "analysis"}),
        "composition": frozenset({"composition", "config", "application", "infrastructure", "analysis", "domain"}),
        "cli": frozenset({"cli", "composition"}),
    }
    return tuple(
        violation for path in root.rglob("*.py") for violation in _path_layer_violations(path, root, allowed_targets)
    )


def _path_layer_violations(
    path: Path,
    root: Path,
    allowed_targets: dict[str, frozenset[str]],
) -> tuple[tuple[Path, str], ...]:
    source_layer = _layer(path, root)
    return tuple(
        (path, imported_module)
        for imported_module in _imports(path)
        if _is_forbidden_layer_import(imported_module, allowed_targets[source_layer])
    )


def _is_forbidden_layer_import(imported_module: str, allowed_targets: frozenset[str]) -> bool:
    target_layer = _imported_layer(imported_module)
    return target_layer is not None and target_layer not in allowed_targets


def _assert_forbidden_imports(source: str, *forbidden: str) -> None:
    rule = archrule("layer direction", "each absent Architecture layer edge is forbidden")
    targets = RuleTargets(rule).match(source)
    RuleConstraints(rule, targets).should_not_import(*forbidden).check("datp_core")


def _layer(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else "domain"


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    direct = tuple(alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names)
    from_imports = tuple(
        node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    return (*direct, *from_imports)


def _imported_layer(module: str) -> str | None:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "datp_core" else None


def _is_assert_never_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == "assert_never"


def _is_wildcard_pattern(pattern: ast.pattern) -> bool:
    return isinstance(pattern, ast.MatchAs) and (pattern.pattern is None or _is_wildcard_pattern(pattern.pattern))


def _matches(path: Path) -> tuple[ast.Match, ...]:
    return tuple(node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.Match))


def _assert_match_is_exhaustive(path: Path, match: ast.Match) -> None:
    if not any(_is_wildcard_pattern(case.pattern) for case in match.cases):
        raise AssertionError(f"closed match lacks an assert_never terminal case: {path}:{match.lineno}")
    for case in _assert_never_cases(match):
        assert case is match.cases[-1]
        assert _is_wildcard_pattern(case.pattern)


def _assert_never_cases(match: ast.Match) -> tuple[ast.match_case, ...]:
    return tuple(case for case in match.cases if any(_is_assert_never_call(call) for call in _calls(case)))


def _calls(case: ast.match_case) -> tuple[ast.Call, ...]:
    module = ast.Module(body=case.body, type_ignores=[])
    return tuple(node for node in ast.walk(module) if isinstance(node, ast.Call))
