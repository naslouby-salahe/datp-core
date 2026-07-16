from pathlib import Path

import pytest

from datp_core.config.compose import ComposeTestConfigurationRequest, compose_test_configuration
from datp_core.config.locking import ProtocolLockStatus, ProtocolLockVerificationMode
from datp_core.domain.errors import ConfigurationError


def test_protocol_lock_verifies_the_resolved_catalogue() -> None:
    result = compose_test_configuration(
        ComposeTestConfigurationRequest(
            configuration_root=Path(__file__).resolve().parents[3] / "configs",
            test_profile_id="unit",
            protocol_lock_mode=ProtocolLockVerificationMode.REQUIRED,
        )
    )

    assert result.protocol_lock.status is ProtocolLockStatus.VERIFIED


def test_protocol_lock_detects_a_scientific_document_change(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parents[3] / "configs"
    copied_root = tmp_path / "configs"
    for source in source_root.rglob("*.yaml"):
        destination = copied_root / source.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(), encoding="utf-8")
    lock_source = source_root / "locks" / "protocol-lock.json"
    lock_destination = copied_root / "locks" / "protocol-lock.json"
    lock_destination.parent.mkdir(parents=True, exist_ok=True)
    lock_destination.write_text(lock_source.read_text(), encoding="utf-8")
    thresholds_path = copied_root / "scientific" / "thresholds.yaml"
    thresholds_path.write_text(
        thresholds_path.read_text(encoding="utf-8").replace('"0.99"', '"0.98"'), encoding="utf-8"
    )

    with pytest.raises(ConfigurationError):
        compose_test_configuration(
            ComposeTestConfigurationRequest(
                configuration_root=copied_root,
                test_profile_id="unit",
                protocol_lock_mode=ProtocolLockVerificationMode.REQUIRED,
            )
        )
