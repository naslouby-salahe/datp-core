import ast
from pathlib import Path

import pytest

from datp_core.domain.enums import CentralizedThresholdMethod, FederatedThresholdMethod
from datp_core.domain.errors import LeakageError
from datp_core.pipeline.decision.centralized import (
    reject_centralized_as_federated_threshold_policy,
    reject_centralized_in_federated_threshold_comparison,
    reject_centralized_threshold_in_federated_dispatch,
    reject_cross_client_cv_fpr_from_pooled_centralized,
)

ROOT = Path(__file__).resolve().parents[2]
CENTRALIZED_ROOT = ROOT / "src" / "datp_core" / "centralized_reference"
THRESHOLDING_ROOT = ROOT / "src" / "datp_core" / "thresholding"


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return tuple(modules)


def test_superseded_centralized_package_is_deleted() -> None:
    assert not CENTRALIZED_ROOT.exists()


def test_thresholding_package_does_not_import_deleted_centralized_reference() -> None:
    violations = tuple(
        str(path.relative_to(ROOT))
        for path in sorted(THRESHOLDING_ROOT.rglob("*.py"))
        if any(module.startswith("datp_core.centralized_reference") for module in _imported_modules(path))
    )
    assert not violations


def test_runtime_guards_block_ladder_and_dispatch_contamination() -> None:
    with pytest.raises(LeakageError):
        reject_centralized_threshold_in_federated_dispatch(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
    with pytest.raises(LeakageError):
        reject_centralized_as_federated_threshold_policy(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
    with pytest.raises(LeakageError):
        reject_cross_client_cv_fpr_from_pooled_centralized()
    with pytest.raises(LeakageError):
        reject_centralized_in_federated_threshold_comparison(FederatedThresholdMethod.LOCAL_THRESHOLD)
