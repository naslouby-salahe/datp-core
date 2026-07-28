import ast
import re
from pathlib import Path

PROHIBITED_IDENTITIES = frozenset(
    (
        "Regime A",
        "Regime B",
        "Regime C",
        "Regime D",
        "B0",
        "B1",
        "B2",
        "B3",
        "B4",
        "baseline_1",
        "baseline_2",
        "policy_1",
        "experiment_v2",
    )
)
OPAQUE_IDENTIFIER = re.compile(r"^(?:regime_[a-d]|b[0-4]|baseline_[0-9]+|policy_[0-9]+|experiment_v[0-9]+)$")


def source_strings_and_identifiers(source_path: Path) -> tuple[frozenset[str], frozenset[str]]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    strings = frozenset(
        node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    identifiers = frozenset(node.id for node in ast.walk(tree) if isinstance(node, ast.Name)) | frozenset(
        node.name for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return strings, identifiers


def test_source_has_no_opaque_scientific_identity_or_serialized_protocol_value() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    for source_path in source_root.rglob("*.py"):
        strings, identifiers = source_strings_and_identifiers(source_path)
        assert PROHIBITED_IDENTITIES.isdisjoint(strings), source_path
        assert not any(OPAQUE_IDENTIFIER.fullmatch(identifier.lower()) for identifier in identifiers), source_path


def test_prohibited_identity_detector_rejects_known_legacy_shorthand(tmp_path: Path) -> None:
    source = "\n".join(f"identity = {identity!r}" for identity in PROHIBITED_IDENTITIES)
    source_path = tmp_path / "opaque_identity.py"
    source_path.write_text(source, encoding="utf-8")
    strings, identifiers = source_strings_and_identifiers(source_path)
    assert not PROHIBITED_IDENTITIES.isdisjoint(strings)
    assert identifiers == frozenset(("identity",))
