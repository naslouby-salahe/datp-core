from pathlib import Path

import pytest

from datp_core.data.nbaiot.schema import (
    NBAIOT_DEVICE_IDENTITIES,
    NBAIOT_FEATURE_COLUMNS,
    NBaIoTAttackFamily,
    NBaIoTAttackSubtype,
    NBaIoTDevice,
    NBaIoTSourceIdentity,
    NBaIoTSourceLabel,
    parse_source_identity,
)


def test_audited_feature_and_device_counts() -> None:
    assert len(NBAIOT_FEATURE_COLUMNS) == 115
    assert len(NBAIOT_DEVICE_IDENTITIES) == 9


def test_unknown_nbaio_path_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_source_identity(Path("unknown/benign_traffic.csv"))


def test_audited_attack_directory_is_interpreted_without_filename_inference() -> None:
    assert parse_source_identity(Path("Danmini_Doorbell/gafgyt_attacks/udp.csv")) == NBaIoTSourceIdentity(
        device=NBaIoTDevice.DANMINI_DOORBELL,
        source_label=NBaIoTSourceLabel.ATTACK,
        attack_family=NBaIoTAttackFamily.GAFGYT,
        attack_subtype=NBaIoTAttackSubtype.UDP,
    )


def test_demonstration_file_is_not_an_accepted_source() -> None:
    with pytest.raises(ValueError):
        parse_source_identity(Path("demonstrate_structure.csv"))
