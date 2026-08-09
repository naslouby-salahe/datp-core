import ast
import inspect
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

from datp_core.core.errors import (
    AnchorReproductionError,
    ArtifactIntegrityError,
    CapabilityError,
    DataIntegrityError,
    DatpCoreError,
    ErrorMessage,
    ExecutionStateError,
    InfeasibleExperimentError,
    LeakageError,
    ProtocolValidationError,
    ScientificContractError,
    SerializationSafetyError,
    UnresolvedScientificValueError,
)
from datp_core.core.identifiers import ContractSubject


class _UnresolvedValueReason(StrEnum):
    NOT_SOURCE_BACKED = "not_source_backed"


DIRECT_ERRORS = (
    ScientificContractError,
    CapabilityError,
    InfeasibleExperimentError,
    DataIntegrityError,
    LeakageError,
    AnchorReproductionError,
    ProtocolValidationError,
    SerializationSafetyError,
    ArtifactIntegrityError,
    ExecutionStateError,
)


def test_error_hierarchy_is_shallow_and_explicit() -> None:
    assert all(issubclass(error, DatpCoreError) for error in DIRECT_ERRORS)
    assert UnresolvedScientificValueError.__bases__ == (ScientificContractError,)
    assert all(error.__bases__ == (DatpCoreError,) for error in DIRECT_ERRORS)


def test_errors_preserve_stable_message_and_named_context() -> None:
    error = UnresolvedScientificValueError(
        ErrorMessage("missing quantile"),
        subject=ContractSubject.QUANTILE,
        reason=_UnresolvedValueReason.NOT_SOURCE_BACKED,
    )
    assert str(error) == "missing quantile"
    assert error.message == "missing quantile"
    assert error.subject is ContractSubject.QUANTILE
    assert error.reason is _UnresolvedValueReason.NOT_SOURCE_BACKED
    assert not isinstance(error.subject, Mapping)


def test_errors_do_not_accept_arbitrary_dictionary_context() -> None:
    parameters = inspect.signature(DatpCoreError).parameters
    assert set(parameters) == {"message", "subject", "reason"}
    assert all(parameter.kind is not inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())


def test_errors_module_does_not_swallow_broad_exceptions() -> None:
    source_path = Path(__file__).parents[3] / "src" / "datp_core" / "core" / "errors.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    broad_handlers = tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler)
        and (node.type is None or (isinstance(node.type, ast.Name) and node.type.id in {"BaseException", "Exception"}))
    )
    assert not broad_handlers
