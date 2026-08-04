import ast
from pathlib import Path

import pytest

from datp_core.centralized_reference.evaluation import (
    reject_centralized_as_federated_threshold_policy,
    reject_centralized_in_federated_threshold_comparison,
    reject_cross_client_cv_fpr_from_pooled_centralized,
)
from datp_core.centralized_reference.thresholding import reject_centralized_threshold_in_federated_dispatch
from datp_core.domain.enums import CentralizedThresholdMethod, FederatedThresholdMethod
from datp_core.domain.errors import LeakageError

ROOT = Path(__file__).resolve().parents[2]
CENTRALIZED_ROOT = ROOT / "src" / "datp_core" / "centralized_reference"
THRESHOLDING_ROOT = ROOT / "src" / "datp_core" / "thresholding"
FORBIDDEN_CENTRALIZED_IMPORTS = (
    "datp_core.thresholding",
    "datp_core.learning.federated",
    "datp_core.scoring",
)
FORBIDDEN_THRESHOLDING_IMPORT = "datp_core.centralized_reference"


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return tuple(modules)


def _assert_no_forbidden_prefix(modules: tuple[str, ...], forbidden_prefixes: tuple[str, ...], path: Path) -> None:
    for module in modules:
        for prefix in forbidden_prefixes:
            assert not module.startswith(prefix), f"{path} imports forbidden module {module}"


def test_centralized_package_does_not_import_federated_thresholding() -> None:
    for path in sorted(CENTRALIZED_ROOT.glob("*.py")):
        _assert_no_forbidden_prefix(_imported_modules(path), FORBIDDEN_CENTRALIZED_IMPORTS, path)


def test_thresholding_package_does_not_import_centralized_reference() -> None:
    for path in sorted(THRESHOLDING_ROOT.glob("*.py")):
        _assert_no_forbidden_prefix(_imported_modules(path), (FORBIDDEN_THRESHOLDING_IMPORT,), path)


def test_runtime_guards_block_ladder_and_dispatch_contamination() -> None:
    with pytest.raises(LeakageError):
        reject_centralized_threshold_in_federated_dispatch(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
    with pytest.raises(LeakageError):
        reject_centralized_as_federated_threshold_policy(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
    with pytest.raises(LeakageError):
        reject_cross_client_cv_fpr_from_pooled_centralized()
    with pytest.raises(LeakageError):
        reject_centralized_in_federated_threshold_comparison(FederatedThresholdMethod.LOCAL_THRESHOLD)
