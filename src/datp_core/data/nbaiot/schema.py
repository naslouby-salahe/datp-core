"""Audited N-BaIoT source schema and path identities."""

from enum import StrEnum
from pathlib import Path

import pyarrow as pa

from datp_core.data.contracts import (
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalProvenanceColumn,
    CanonicalSchema,
    ColumnLogicalType,
)
from datp_core.data.materialization import (
    canonical_provenance_arrow_field,
    canonical_provenance_column,
    canonical_schema_checksum,
)
from datp_core.core.identifiers import DatasetId
from datp_core.core.numeric import CanonicalColumnPosition


class NBaIoTDevice(StrEnum):
    DANMINI_DOORBELL = "danmini_doorbell"
    ECOBEE_THERMOSTAT = "ecobee_thermostat"
    ENNIO_DOORBELL = "ennio_doorbell"
    PHILIPS_B120N10_BABY_MONITOR = "philips_b120n10_baby_monitor"
    PROVISION_PT_737E_SECURITY_CAMERA = "provision_pt_737e_security_camera"
    PROVISION_PT_838_SECURITY_CAMERA = "provision_pt_838_security_camera"
    SAMSUNG_SNH_1011_N_WEBCAM = "samsung_snh_1011_n_webcam"
    SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA = "simplehome_xcs7_1002_wht_security_camera"
    SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA = "simplehome_xcs7_1003_wht_security_camera"


class NBaIoTDeviceFamily(StrEnum):
    BABY_MONITOR = "baby_monitor"
    DOORBELL = "doorbell"
    SECURITY_CAMERA = "security_camera"
    THERMOSTAT = "thermostat"
    WEBCAM = "webcam"


class NBaIoTArtifactName(StrEnum):
    CSV_SUFFIX = ".csv"
    BENIGN_TRAFFIC_FILE = "benign_traffic.csv"
    ATTACK_DIRECTORY_SUFFIX = "_attacks"
    STRUCTURE_DEMONSTRATION_FILE = "demonstrate_structure.csv"


class NBaIoTCanonicalColumn(StrEnum):
    PHYSICAL_CLIENT_ID = "physical_client_id"
    PHYSICAL_DEVICE_FAMILY = "physical_device_family"
    RAW_LABEL = "raw_label"
    ATTACK_FAMILY = "attack_family"
    ATTACK_SUBTYPE = "attack_subtype"


class NBaIoTSourceLabel(StrEnum):
    BENIGN = "benign"
    ATTACK = "attack"


class NBaIoTColumnSource(StrEnum):
    AUDITED_DEVICE_PATH = "audited device path"
    TABLE_III_DEVICE_TYPE = "N-BaIoT Table III device type"
    AUDITED_SOURCE_PATH = "audited source path"


_WINDOWS: tuple[str, ...] = ("L5", "L3", "L1", "L0.1", "L0.01")
_BASIC_STATISTICS: tuple[str, ...] = ("weight", "mean", "variance")
_CHANNEL_STATISTICS: tuple[str, ...] = ("weight", "mean", "std", "magnitude", "radius", "covariance", "pcc")


def _feature_columns() -> tuple[str, ...]:
    return (
        _feature_group("MI_dir", _BASIC_STATISTICS)
        + _feature_group("H", _BASIC_STATISTICS)
        + _feature_group("HH", _CHANNEL_STATISTICS)
        + _feature_group("HH_jit", _BASIC_STATISTICS)
        + _feature_group("HpHp", _CHANNEL_STATISTICS)
    )


def _feature_group(prefix: str, statistics: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{prefix}_{window}_{statistic}" for window in _WINDOWS for statistic in statistics)


NBAIOT_FEATURE_COLUMNS = _feature_columns()
NBAIOT_DEVICE_IDENTITIES: tuple[str, ...] = tuple(device.value for device in NBaIoTDevice)
NBAIOT_DEVICE_FAMILIES: tuple[str, ...] = tuple(family.value for family in NBaIoTDeviceFamily)
NBAIOT_ATTACK_FAMILIES: tuple[str, ...] = ("gafgyt", "mirai")
NBAIOT_ATTACK_SUBTYPES: tuple[str, ...] = ("ack", "combo", "junk", "scan", "syn", "tcp", "udp", "udpplain")


NBAIOT_PROVENANCE_COLUMNS: tuple[str, ...] = tuple(CanonicalProvenanceColumn)


def _canonical_columns() -> tuple[CanonicalColumn, ...]:
    feature_columns = tuple(
        CanonicalColumn(
            column,
            column,
            ColumnLogicalType.FLOAT64,
            CanonicalColumnRole.FEATURE,
            True,
            CanonicalColumnPosition(position),
        )
        for position, column in enumerate(NBAIOT_FEATURE_COLUMNS)
    )
    provenance_columns = tuple(
        canonical_provenance_column(column, len(feature_columns) + index)
        for index, column in enumerate(tuple(CanonicalProvenanceColumn)[:-1])
    )
    evidence_start = len(feature_columns) + len(provenance_columns)
    evidence_columns = (
        CanonicalColumn(
            NBaIoTCanonicalColumn.PHYSICAL_CLIENT_ID,
            NBaIoTColumnSource.AUDITED_DEVICE_PATH,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            CanonicalColumnPosition(evidence_start),
        ),
        CanonicalColumn(
            NBaIoTCanonicalColumn.PHYSICAL_DEVICE_FAMILY,
            NBaIoTColumnSource.TABLE_III_DEVICE_TYPE,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            CanonicalColumnPosition(evidence_start + 1),
        ),
        CanonicalColumn(
            NBaIoTCanonicalColumn.RAW_LABEL,
            NBaIoTColumnSource.AUDITED_SOURCE_PATH,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(evidence_start + 2),
        ),
        CanonicalColumn(
            NBaIoTCanonicalColumn.ATTACK_FAMILY,
            NBaIoTColumnSource.AUDITED_SOURCE_PATH,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.RAW_EVIDENCE,
            True,
            CanonicalColumnPosition(evidence_start + 3),
        ),
        CanonicalColumn(
            NBaIoTCanonicalColumn.ATTACK_SUBTYPE,
            NBaIoTColumnSource.AUDITED_SOURCE_PATH,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.RAW_EVIDENCE,
            True,
            CanonicalColumnPosition(evidence_start + 4),
        ),
    )
    stable_identity = canonical_provenance_column(
        CanonicalProvenanceColumn.STABLE_ROW_ID,
        evidence_start + len(evidence_columns),
    )
    return feature_columns + provenance_columns + evidence_columns + (stable_identity,)


def _arrow_schema() -> pa.Schema:
    return pa.schema(
        tuple(pa.field(column, pa.float64()) for column in NBAIOT_FEATURE_COLUMNS)
        + (
            canonical_provenance_arrow_field(CanonicalProvenanceColumn.SOURCE_ROW_INDEX),
            canonical_provenance_arrow_field(CanonicalProvenanceColumn.SOURCE_PATH),
            pa.field(NBaIoTCanonicalColumn.PHYSICAL_CLIENT_ID, pa.large_string()),
            pa.field(NBaIoTCanonicalColumn.PHYSICAL_DEVICE_FAMILY, pa.large_string()),
            pa.field(NBaIoTCanonicalColumn.RAW_LABEL, pa.large_string()),
            pa.field(NBaIoTCanonicalColumn.ATTACK_FAMILY, pa.large_string()),
            pa.field(NBaIoTCanonicalColumn.ATTACK_SUBTYPE, pa.large_string()),
            canonical_provenance_arrow_field(CanonicalProvenanceColumn.STABLE_ROW_ID),
        )
    )


NBAIOT_CANONICAL_COLUMNS = _canonical_columns()
NBAIOT_ARROW_SCHEMA = _arrow_schema()
NBAIOT_SCHEMA = CanonicalSchema(
    dataset=DatasetId.NBAIOT,
    columns=NBAIOT_CANONICAL_COLUMNS,
    feature_columns=NBAIOT_FEATURE_COLUMNS,
    label_columns=(NBaIoTCanonicalColumn.RAW_LABEL,),
    provenance_columns=NBAIOT_PROVENANCE_COLUMNS,
    physical_schema=NBAIOT_ARROW_SCHEMA.to_string(show_field_metadata=True, show_schema_metadata=True),
    checksum=canonical_schema_checksum(DatasetId.NBAIOT, NBAIOT_CANONICAL_COLUMNS, NBAIOT_ARROW_SCHEMA),
)


def parse_source_identity(path: Path) -> tuple[str, str, str | None, str | None]:
    parts = path.parts
    if path.suffix != NBaIoTArtifactName.CSV_SUFFIX or len(parts) < 2:
        raise ValueError("N-BaIoT sources must be extracted CSV files")
    if path.name == NBaIoTArtifactName.BENIGN_TRAFFIC_FILE:
        return _benign_source_identity(parts)
    return _attack_source_identity(parts, path.stem)


def source_relative_path(path: Path) -> Path:
    if path.name == NBaIoTArtifactName.BENIGN_TRAFFIC_FILE:
        return Path(path.parent.name, path.name)
    return Path(path.parent.parent.name, path.parent.name, path.name)


def _benign_source_identity(parts: tuple[str, ...]) -> tuple[str, str, None, None]:
    device = _device(parts[-2]).value
    return device, NBaIoTSourceLabel.BENIGN.value, None, None


def _attack_source_identity(parts: tuple[str, ...], subtype: str) -> tuple[str, str, str, str]:
    device = _device(parts[-3]).value
    attack_directory = parts[-2]
    if not attack_directory.endswith(NBaIoTArtifactName.ATTACK_DIRECTORY_SUFFIX):
        raise ValueError("unrecognized N-BaIoT attack path")
    family = attack_directory.removesuffix(NBaIoTArtifactName.ATTACK_DIRECTORY_SUFFIX)
    if family not in NBAIOT_ATTACK_FAMILIES or subtype not in NBAIOT_ATTACK_SUBTYPES:
        raise ValueError("unrecognized N-BaIoT attack path")
    return device, NBaIoTSourceLabel.ATTACK.value, family, subtype


def device_family(device_identity: str) -> NBaIoTDeviceFamily:
    device = _device(device_identity)
    match device:
        case NBaIoTDevice.DANMINI_DOORBELL | NBaIoTDevice.ENNIO_DOORBELL:
            return NBaIoTDeviceFamily.DOORBELL
        case NBaIoTDevice.ECOBEE_THERMOSTAT:
            return NBaIoTDeviceFamily.THERMOSTAT
        case NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR:
            return NBaIoTDeviceFamily.BABY_MONITOR
        case (
            NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA
            | NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA
            | NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA
            | NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA
        ):
            return NBaIoTDeviceFamily.SECURITY_CAMERA
        case NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM:
            return NBaIoTDeviceFamily.WEBCAM


def _device(value: str) -> NBaIoTDevice:
    try:
        return NBaIoTDevice(value.lower())
    except ValueError as error:
        raise ValueError("unrecognized N-BaIoT device path") from error
