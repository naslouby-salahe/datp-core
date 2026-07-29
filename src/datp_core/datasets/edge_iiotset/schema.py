"""Audited Edge-IIoTset CSV schema and source identity rules."""

from enum import StrEnum
from pathlib import Path

import pyarrow as pa

from datp_core.datasets.materialization import (
    canonical_provenance_arrow_field,
    canonical_provenance_column,
    canonical_schema_checksum,
)
from datp_core.datasets.models import (
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalProvenanceColumn,
    CanonicalSchema,
    ColumnLogicalType,
)
from datp_core.domain.enums import DatasetId


class EdgeArtifactSuffix(StrEnum):
    CSV = ".csv"
    PCAP = ".pcap"


class EdgeArtifactName(StrEnum):
    DATASET_BUNDLE_DIRECTORY = "Edge-IIoTset dataset"
    NORMAL_TRAFFIC_DIRECTORY = "Normal traffic"
    ATTACK_TRAFFIC_DIRECTORY = "Attack traffic"
    ATTACK_FILE_SUFFIX = "_attack.csv"


class EdgeAssetRole(StrEnum):
    STATIC_BENIGN = "static_benign"
    TEMPORAL_BENIGN = "temporal_benign"
    UNASSIGNED_ATTACK = "unassigned_attack"


class EdgeSensorGroup(StrEnum):
    DISTANCE = "Distance"
    FLAME_SENSOR = "Flame_Sensor"
    HEART_RATE = "Heart_Rate"
    IR_RECEIVER = "IR_Receiver"
    MODBUS = "Modbus"
    SOIL_MOISTURE = "Soil_Moisture"
    SOUND_SENSOR = "Sound_Sensor"
    TEMPERATURE_AND_HUMIDITY = "Temperature_and_Humidity"
    WATER_LEVEL = "Water_Level"
    PH_VALUE = "phValue"


class EdgeCanonicalColumn(StrEnum):
    RAW_TIMESTAMP = "raw_timestamp"
    ATTACK_LABEL = "attack_label"
    ATTACK_TYPE = "attack_type"
    CAPTURE_TIMESTAMP = "capture_timestamp"
    SOURCE_FOLDER = "source_folder"
    BENIGN_SENSOR_GROUP = "benign_sensor_group"


class EdgeRawColumn(StrEnum):
    TIMESTAMP = "frame.time"
    ATTACK_LABEL = "Attack_label"
    ATTACK_TYPE = "Attack_type"


EDGE_RAW_COLUMNS: tuple[str, ...] = tuple(
    (
        "frame.time,ip.src_host,ip.dst_host,arp.dst.proto_ipv4,arp.opcode,arp.hw.size,arp.src.proto_ipv4,"
        "icmp.checksum,icmp.seq_le,icmp.transmit_timestamp,icmp.unused,http.file_data,http.content_length,"
        "http.request.uri.query,http.request.method,http.referer,http.request.full_uri,http.request.version,"
        "http.response,http.tls_port,tcp.ack,tcp.ack_raw,tcp.checksum,tcp.connection.fin,tcp.connection.rst,"
        "tcp.connection.syn,tcp.connection.synack,tcp.dstport,tcp.flags,tcp.flags.ack,tcp.len,tcp.options,"
        "tcp.payload,tcp.seq,tcp.srcport,udp.port,udp.stream,udp.time_delta,dns.qry.name,dns.qry.name.len,"
        "dns.qry.qu,dns.qry.type,dns.retransmission,dns.retransmit_request,dns.retransmit_request_in,"
        "mqtt.conack.flags,mqtt.conflag.cleansess,mqtt.conflags,mqtt.hdrflags,mqtt.len,mqtt.msg_decoded_as,"
        "mqtt.msg,mqtt.msgtype,mqtt.proto_len,mqtt.protoname,mqtt.topic,mqtt.topic_len,mqtt.ver,mbtcp.len,"
        "mbtcp.trans_id,mbtcp.unit_id,Attack_label,Attack_type"
    ).split(",")
)
EDGE_FEATURE_COLUMNS: tuple[str, ...] = EDGE_RAW_COLUMNS[:-2]
EDGE_BENIGN_SENSOR_GROUPS: tuple[EdgeSensorGroup, ...] = (
    EdgeSensorGroup.DISTANCE,
    EdgeSensorGroup.FLAME_SENSOR,
    EdgeSensorGroup.HEART_RATE,
    EdgeSensorGroup.IR_RECEIVER,
    EdgeSensorGroup.MODBUS,
    EdgeSensorGroup.SOIL_MOISTURE,
    EdgeSensorGroup.SOUND_SENSOR,
    EdgeSensorGroup.TEMPERATURE_AND_HUMIDITY,
    EdgeSensorGroup.WATER_LEVEL,
    EdgeSensorGroup.PH_VALUE,
)

EDGE_CANONICAL_FEATURE_COLUMNS: tuple[str, ...] = (EdgeCanonicalColumn.RAW_TIMESTAMP,) + EDGE_FEATURE_COLUMNS[1:]
EDGE_PROVENANCE_COLUMNS: tuple[str, ...] = (
    CanonicalProvenanceColumn.SOURCE_ROW_INDEX,
    EdgeCanonicalColumn.CAPTURE_TIMESTAMP,
    CanonicalProvenanceColumn.SOURCE_PATH,
    CanonicalProvenanceColumn.STABLE_ROW_ID,
)


def _canonical_columns() -> tuple[CanonicalColumn, ...]:
    feature_columns = tuple(
        CanonicalColumn(column, source, ColumnLogicalType.STRING, CanonicalColumnRole.FEATURE, True, position)
        for position, (column, source) in enumerate(
            zip(EDGE_CANONICAL_FEATURE_COLUMNS, EDGE_FEATURE_COLUMNS, strict=True)
        )
    )
    trailing_start = len(feature_columns)
    trailing_columns = (
        CanonicalColumn(
            EdgeCanonicalColumn.ATTACK_LABEL,
            EdgeRawColumn.ATTACK_LABEL,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            trailing_start,
        ),
        CanonicalColumn(
            EdgeCanonicalColumn.ATTACK_TYPE,
            EdgeRawColumn.ATTACK_TYPE,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            trailing_start + 1,
        ),
        canonical_provenance_column(CanonicalProvenanceColumn.SOURCE_ROW_INDEX, trailing_start + 2),
        CanonicalColumn(
            EdgeCanonicalColumn.CAPTURE_TIMESTAMP,
            "paired raw PCAP capture timestamp",
            ColumnLogicalType.TIMESTAMP_NS_UTC,
            CanonicalColumnRole.PROVENANCE,
            True,
            trailing_start + 3,
        ),
        CanonicalColumn(
            EdgeCanonicalColumn.SOURCE_FOLDER,
            "raw source folder",
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            trailing_start + 4,
        ),
        CanonicalColumn(
            EdgeCanonicalColumn.BENIGN_SENSOR_GROUP,
            "audited benign source folder",
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            trailing_start + 5,
        ),
        canonical_provenance_column(CanonicalProvenanceColumn.SOURCE_PATH, trailing_start + 6),
        canonical_provenance_column(CanonicalProvenanceColumn.STABLE_ROW_ID, trailing_start + 7),
    )
    return feature_columns + trailing_columns


EDGE_CANONICAL_COLUMNS = _canonical_columns()
EDGE_ARROW_SCHEMA = pa.schema(
    tuple(pa.field(column, pa.large_string()) for column in EDGE_CANONICAL_FEATURE_COLUMNS)
    + (
        pa.field(EdgeCanonicalColumn.ATTACK_LABEL, pa.large_string()),
        pa.field(EdgeCanonicalColumn.ATTACK_TYPE, pa.large_string()),
        canonical_provenance_arrow_field(CanonicalProvenanceColumn.SOURCE_ROW_INDEX),
        pa.field(EdgeCanonicalColumn.CAPTURE_TIMESTAMP, pa.timestamp("ns", tz="UTC")),
        pa.field(EdgeCanonicalColumn.SOURCE_FOLDER, pa.large_string()),
        pa.field(EdgeCanonicalColumn.BENIGN_SENSOR_GROUP, pa.large_string()),
        canonical_provenance_arrow_field(CanonicalProvenanceColumn.SOURCE_PATH),
        canonical_provenance_arrow_field(CanonicalProvenanceColumn.STABLE_ROW_ID),
    )
)
EDGE_SCHEMA = CanonicalSchema(
    dataset=DatasetId.EDGE_IIOTSET,
    columns=EDGE_CANONICAL_COLUMNS,
    feature_columns=EDGE_CANONICAL_FEATURE_COLUMNS,
    label_columns=(EdgeCanonicalColumn.ATTACK_LABEL, EdgeCanonicalColumn.ATTACK_TYPE),
    provenance_columns=EDGE_PROVENANCE_COLUMNS,
    physical_schema=EDGE_ARROW_SCHEMA.to_string(show_field_metadata=True, show_schema_metadata=True),
    checksum=canonical_schema_checksum(DatasetId.EDGE_IIOTSET, EDGE_CANONICAL_COLUMNS, EDGE_ARROW_SCHEMA),
)


def benign_sensor_group(path: Path) -> EdgeSensorGroup:
    if path.suffix != EdgeArtifactSuffix.CSV:
        raise ValueError("unrecognized Edge benign sensor source")
    try:
        group = EdgeSensorGroup(path.parent.name)
    except ValueError as error:
        raise ValueError("unrecognized Edge benign sensor source") from error
    if path.stem != group.value:
        raise ValueError("Edge benign source filename must match its sensor-group folder")
    return group


def is_attack_source(path: Path) -> bool:
    return (
        path.suffix == EdgeArtifactSuffix.CSV
        and path.parent.name == EdgeArtifactName.ATTACK_TRAFFIC_DIRECTORY
        and path.name.endswith(EdgeArtifactName.ATTACK_FILE_SUFFIX)
    )


def source_relative_path(path: Path) -> Path:
    if path.parent.parent == path.parent:
        raise ValueError("Edge sources must retain their raw traffic directory")
    return Path(path.parent.parent.name, path.parent.name, path.name)
