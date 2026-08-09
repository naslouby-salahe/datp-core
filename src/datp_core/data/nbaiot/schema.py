"""Audited N-BaIoT source schema and path identities."""

from enum import StrEnum
from pathlib import Path

import pyarrow as pa

from datp_core.core.identifiers import (
    AttackSubtypeToken,
    ColumnName,
    DatasetId,
    FeatureNamePrefix,
    PhysicalSchemaText,
    SourcePathPart,
)
from datp_core.core.numeric import CanonicalColumnPosition
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


class NBaIoTWindow(StrEnum):
    L5 = "L5"
    L3 = "L3"
    L1 = "L1"
    L0_1 = "L0.1"
    L0_01 = "L0.01"


class NBaIoTBasicStatistic(StrEnum):
    WEIGHT = "weight"
    MEAN = "mean"
    VARIANCE = "variance"


class NBaIoTChannelStatistic(StrEnum):
    WEIGHT = "weight"
    MEAN = "mean"
    STD = "std"
    MAGNITUDE = "magnitude"
    RADIUS = "radius"
    COVARIANCE = "covariance"
    PCC = "pcc"


class NBaIoTAttackFamily(StrEnum):
    GAFGYT = "gafgyt"
    MIRAI = "mirai"


class NBaIoTAttackSubtype(StrEnum):
    ACK = "ack"
    COMBO = "combo"
    JUNK = "junk"
    SCAN = "scan"
    SYN = "syn"
    TCP = "tcp"
    UDP = "udp"
    UDPPLAIN = "udpplain"


_WINDOWS: tuple[NBaIoTWindow, ...] = tuple(NBaIoTWindow)
_BASIC_STATISTICS: tuple[NBaIoTBasicStatistic, ...] = tuple(NBaIoTBasicStatistic)
_CHANNEL_STATISTICS: tuple[NBaIoTChannelStatistic, ...] = tuple(NBaIoTChannelStatistic)


def _feature_columns() -> tuple[ColumnName, ...]:
    return (
        _feature_group(FeatureNamePrefix("MI_dir"), _BASIC_STATISTICS)
        + _feature_group(FeatureNamePrefix("H"), _BASIC_STATISTICS)
        + _feature_group(FeatureNamePrefix("HH"), _CHANNEL_STATISTICS)
        + _feature_group(FeatureNamePrefix("HH_jit"), _BASIC_STATISTICS)
        + _feature_group(FeatureNamePrefix("HpHp"), _CHANNEL_STATISTICS)
    )


def _feature_group(
    prefix: FeatureNamePrefix,
    statistics: tuple[NBaIoTBasicStatistic, ...] | tuple[NBaIoTChannelStatistic, ...],
) -> tuple[ColumnName, ...]:
    return tuple(ColumnName(f"{prefix}_{window}_{statistic}") for window in _WINDOWS for statistic in statistics)


NBAIOT_FEATURE_COLUMNS = _feature_columns()
NBAIOT_DEVICE_IDENTITIES: tuple[NBaIoTDevice, ...] = tuple(NBaIoTDevice)
NBAIOT_DEVICE_FAMILIES: tuple[NBaIoTDeviceFamily, ...] = tuple(NBaIoTDeviceFamily)


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
        canonical_provenance_column(column, CanonicalColumnPosition(len(feature_columns) + index))
        for index, column in enumerate(tuple(CanonicalProvenanceColumn)[:-1])
    )
    evidence_start = len(feature_columns) + len(provenance_columns)
    evidence_columns = (
        CanonicalColumn(
            ColumnName(NBaIoTCanonicalColumn.PHYSICAL_CLIENT_ID),
            ColumnName(NBaIoTColumnSource.AUDITED_DEVICE_PATH),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            CanonicalColumnPosition(evidence_start),
        ),
        CanonicalColumn(
            ColumnName(NBaIoTCanonicalColumn.PHYSICAL_DEVICE_FAMILY),
            ColumnName(NBaIoTColumnSource.TABLE_III_DEVICE_TYPE),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            CanonicalColumnPosition(evidence_start + 1),
        ),
        CanonicalColumn(
            ColumnName(NBaIoTCanonicalColumn.RAW_LABEL),
            ColumnName(NBaIoTColumnSource.AUDITED_SOURCE_PATH),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(evidence_start + 2),
        ),
        CanonicalColumn(
            ColumnName(NBaIoTCanonicalColumn.ATTACK_FAMILY),
            ColumnName(NBaIoTColumnSource.AUDITED_SOURCE_PATH),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.RAW_EVIDENCE,
            True,
            CanonicalColumnPosition(evidence_start + 3),
        ),
        CanonicalColumn(
            ColumnName(NBaIoTCanonicalColumn.ATTACK_SUBTYPE),
            ColumnName(NBaIoTColumnSource.AUDITED_SOURCE_PATH),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.RAW_EVIDENCE,
            True,
            CanonicalColumnPosition(evidence_start + 4),
        ),
    )
    stable_identity = canonical_provenance_column(
        CanonicalProvenanceColumn.STABLE_ROW_ID,
        CanonicalColumnPosition(evidence_start + len(evidence_columns)),
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
    label_columns=(ColumnName(NBaIoTCanonicalColumn.RAW_LABEL),),
    provenance_columns=tuple(ColumnName(column) for column in CanonicalProvenanceColumn),
    physical_schema=PhysicalSchemaText(
        NBAIOT_ARROW_SCHEMA.to_string(show_field_metadata=True, show_schema_metadata=True)
    ),
    checksum=canonical_schema_checksum(DatasetId.NBAIOT, NBAIOT_CANONICAL_COLUMNS, NBAIOT_ARROW_SCHEMA),
)


def parse_source_identity(
    path: Path,
) -> tuple[NBaIoTDevice, NBaIoTSourceLabel, NBaIoTAttackFamily | None, NBaIoTAttackSubtype | None]:
    parts = tuple(SourcePathPart(part) for part in path.parts)
    if path.suffix != NBaIoTArtifactName.CSV_SUFFIX or len(parts) < 2:
        raise ValueError("N-BaIoT sources must be extracted CSV files")
    if path.name == NBaIoTArtifactName.BENIGN_TRAFFIC_FILE:
        return _benign_source_identity(parts)
    return _attack_source_identity(parts, AttackSubtypeToken(path.stem))


def source_relative_path(path: Path) -> Path:
    if path.name == NBaIoTArtifactName.BENIGN_TRAFFIC_FILE:
        return Path(path.parent.name, path.name)
    return Path(path.parent.parent.name, path.parent.name, path.name)


def _benign_source_identity(
    parts: tuple[SourcePathPart, ...],
) -> tuple[NBaIoTDevice, NBaIoTSourceLabel, None, None]:
    return _device(parts[-2]), NBaIoTSourceLabel.BENIGN, None, None


def _attack_source_identity(
    parts: tuple[SourcePathPart, ...], subtype: AttackSubtypeToken
) -> tuple[NBaIoTDevice, NBaIoTSourceLabel, NBaIoTAttackFamily, NBaIoTAttackSubtype]:
    device = _device(parts[-3])
    attack_directory = parts[-2]
    if not attack_directory.endswith(NBaIoTArtifactName.ATTACK_DIRECTORY_SUFFIX):
        raise ValueError("unrecognized N-BaIoT attack path")
    family_value = attack_directory.removesuffix(NBaIoTArtifactName.ATTACK_DIRECTORY_SUFFIX)
    try:
        family = NBaIoTAttackFamily(family_value)
        attack_subtype = NBaIoTAttackSubtype(subtype)
    except ValueError as error:
        raise ValueError("unrecognized N-BaIoT attack path") from error
    return device, NBaIoTSourceLabel.ATTACK, family, attack_subtype


def device_family(device: NBaIoTDevice) -> NBaIoTDeviceFamily:
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


def _device(value: SourcePathPart) -> NBaIoTDevice:
    try:
        return NBaIoTDevice(value.lower())
    except ValueError as error:
        raise ValueError("unrecognized N-BaIoT device path") from error
