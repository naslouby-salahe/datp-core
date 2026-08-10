from enum import StrEnum
from pathlib import Path

import pyarrow as pa

from datp_core.core.identifiers import ColumnName, DatasetId, PhysicalSchemaText
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
)


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
    IP_SRC_HOST = "ip.src_host"
    IP_DST_HOST = "ip.dst_host"
    ARP_DST_PROTO_IPV4 = "arp.dst.proto_ipv4"
    ARP_OPCODE = "arp.opcode"
    ARP_HW_SIZE = "arp.hw.size"
    ARP_SRC_PROTO_IPV4 = "arp.src.proto_ipv4"
    ICMP_CHECKSUM = "icmp.checksum"
    ICMP_SEQ_LE = "icmp.seq_le"
    ICMP_TRANSMIT_TIMESTAMP = "icmp.transmit_timestamp"
    ICMP_UNUSED = "icmp.unused"
    HTTP_FILE_DATA = "http.file_data"
    HTTP_CONTENT_LENGTH = "http.content_length"
    HTTP_REQUEST_URI_QUERY = "http.request.uri.query"
    HTTP_REQUEST_METHOD = "http.request.method"
    HTTP_REFERER = "http.referer"
    HTTP_REQUEST_FULL_URI = "http.request.full_uri"
    HTTP_REQUEST_VERSION = "http.request.version"
    HTTP_RESPONSE = "http.response"
    HTTP_TLS_PORT = "http.tls_port"
    TCP_ACK = "tcp.ack"
    TCP_ACK_RAW = "tcp.ack_raw"
    TCP_CHECKSUM = "tcp.checksum"
    TCP_CONNECTION_FIN = "tcp.connection.fin"
    TCP_CONNECTION_RST = "tcp.connection.rst"
    TCP_CONNECTION_SYN = "tcp.connection.syn"
    TCP_CONNECTION_SYNACK = "tcp.connection.synack"
    TCP_DSTPORT = "tcp.dstport"
    TCP_FLAGS = "tcp.flags"
    TCP_FLAGS_ACK = "tcp.flags.ack"
    TCP_LEN = "tcp.len"
    TCP_OPTIONS = "tcp.options"
    TCP_PAYLOAD = "tcp.payload"
    TCP_SEQ = "tcp.seq"
    TCP_SRCPORT = "tcp.srcport"
    UDP_PORT = "udp.port"
    UDP_STREAM = "udp.stream"
    UDP_TIME_DELTA = "udp.time_delta"
    DNS_QRY_NAME = "dns.qry.name"
    DNS_QRY_NAME_LEN = "dns.qry.name.len"
    DNS_QRY_QU = "dns.qry.qu"
    DNS_QRY_TYPE = "dns.qry.type"
    DNS_RETRANSMISSION = "dns.retransmission"
    DNS_RETRANSMIT_REQUEST = "dns.retransmit_request"
    DNS_RETRANSMIT_REQUEST_IN = "dns.retransmit_request_in"
    MQTT_CONACK_FLAGS = "mqtt.conack.flags"
    MQTT_CONFLAG_CLEANSESS = "mqtt.conflag.cleansess"
    MQTT_CONFLAGS = "mqtt.conflags"
    MQTT_HDRFLAGS = "mqtt.hdrflags"
    MQTT_LEN = "mqtt.len"
    MQTT_MSG_DECODED_AS = "mqtt.msg_decoded_as"
    MQTT_MSG = "mqtt.msg"
    MQTT_MSGTYPE = "mqtt.msgtype"
    MQTT_PROTO_LEN = "mqtt.proto_len"
    MQTT_PROTONAME = "mqtt.protoname"
    MQTT_TOPIC = "mqtt.topic"
    MQTT_TOPIC_LEN = "mqtt.topic_len"
    MQTT_VER = "mqtt.ver"
    MBTCP_LEN = "mbtcp.len"
    MBTCP_TRANS_ID = "mbtcp.trans_id"
    MBTCP_UNIT_ID = "mbtcp.unit_id"
    ATTACK_LABEL = "Attack_label"
    ATTACK_TYPE = "Attack_type"


EDGE_RAW_COLUMNS: tuple[EdgeRawColumn, ...] = tuple(EdgeRawColumn)
EDGE_FEATURE_COLUMNS: tuple[EdgeRawColumn, ...] = EDGE_RAW_COLUMNS[:-2]
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

EDGE_CANONICAL_FEATURE_COLUMNS: tuple[ColumnName, ...] = (ColumnName(EdgeCanonicalColumn.RAW_TIMESTAMP),) + tuple(
    ColumnName(column) for column in EDGE_FEATURE_COLUMNS[1:]
)
EDGE_NUMERIC_FEATURE_COLUMNS: tuple[EdgeRawColumn, ...] = (
    EdgeRawColumn.ICMP_SEQ_LE,
    EdgeRawColumn.ICMP_UNUSED,
    EdgeRawColumn.HTTP_FILE_DATA,
    EdgeRawColumn.HTTP_CONTENT_LENGTH,
    EdgeRawColumn.HTTP_REQUEST_URI_QUERY,
    EdgeRawColumn.HTTP_REQUEST_METHOD,
    EdgeRawColumn.HTTP_REFERER,
    EdgeRawColumn.HTTP_REQUEST_FULL_URI,
    EdgeRawColumn.HTTP_REQUEST_VERSION,
    EdgeRawColumn.HTTP_RESPONSE,
    EdgeRawColumn.HTTP_TLS_PORT,
    EdgeRawColumn.TCP_ACK,
    EdgeRawColumn.TCP_CONNECTION_FIN,
    EdgeRawColumn.TCP_CONNECTION_RST,
    EdgeRawColumn.TCP_CONNECTION_SYN,
    EdgeRawColumn.TCP_CONNECTION_SYNACK,
    EdgeRawColumn.TCP_FLAGS_ACK,
    EdgeRawColumn.TCP_SEQ,
    EdgeRawColumn.TCP_SRCPORT,
    EdgeRawColumn.UDP_PORT,
    EdgeRawColumn.UDP_STREAM,
    EdgeRawColumn.UDP_TIME_DELTA,
    EdgeRawColumn.DNS_QRY_TYPE,
    EdgeRawColumn.DNS_RETRANSMISSION,
    EdgeRawColumn.DNS_RETRANSMIT_REQUEST,
    EdgeRawColumn.DNS_RETRANSMIT_REQUEST_IN,
    EdgeRawColumn.MQTT_CONFLAG_CLEANSESS,
    EdgeRawColumn.MQTT_MSG_DECODED_AS,
    EdgeRawColumn.MQTT_MSGTYPE,
    EdgeRawColumn.MQTT_TOPIC_LEN,
    EdgeRawColumn.MQTT_VER,
    EdgeRawColumn.MBTCP_TRANS_ID,
    EdgeRawColumn.MBTCP_UNIT_ID,
)
EDGE_PROVENANCE_COLUMNS: tuple[ColumnName, ...] = (
    ColumnName(CanonicalProvenanceColumn.SOURCE_ROW_INDEX),
    ColumnName(EdgeCanonicalColumn.CAPTURE_TIMESTAMP),
    ColumnName(CanonicalProvenanceColumn.SOURCE_PATH),
    ColumnName(CanonicalProvenanceColumn.STABLE_ROW_ID),
)


def _canonical_columns() -> tuple[CanonicalColumn, ...]:
    feature_columns = tuple(
        CanonicalColumn(
            column,
            ColumnName(source),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.FEATURE,
            True,
            CanonicalColumnPosition(position),
        )
        for position, (column, source) in enumerate(
            zip(EDGE_CANONICAL_FEATURE_COLUMNS, EDGE_FEATURE_COLUMNS, strict=True)
        )
    )
    trailing_start = len(feature_columns)
    trailing_columns = (
        CanonicalColumn(
            ColumnName(EdgeCanonicalColumn.ATTACK_LABEL),
            ColumnName(EdgeRawColumn.ATTACK_LABEL),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(trailing_start),
        ),
        CanonicalColumn(
            ColumnName(EdgeCanonicalColumn.ATTACK_TYPE),
            ColumnName(EdgeRawColumn.ATTACK_TYPE),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(trailing_start + 1),
        ),
        canonical_provenance_column(
            CanonicalProvenanceColumn.SOURCE_ROW_INDEX, CanonicalColumnPosition(trailing_start + 2)
        ),
        CanonicalColumn(
            ColumnName(EdgeCanonicalColumn.CAPTURE_TIMESTAMP),
            ColumnName("paired raw PCAP capture timestamp"),
            ColumnLogicalType.TIMESTAMP_NS_UTC,
            CanonicalColumnRole.PROVENANCE,
            True,
            CanonicalColumnPosition(trailing_start + 3),
        ),
        CanonicalColumn(
            ColumnName(EdgeCanonicalColumn.SOURCE_FOLDER),
            ColumnName("raw source folder"),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            CanonicalColumnPosition(trailing_start + 4),
        ),
        CanonicalColumn(
            ColumnName(EdgeCanonicalColumn.BENIGN_SENSOR_GROUP),
            ColumnName("audited benign source folder"),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.IDENTITY,
            True,
            CanonicalColumnPosition(trailing_start + 5),
        ),
        canonical_provenance_column(CanonicalProvenanceColumn.SOURCE_PATH, CanonicalColumnPosition(trailing_start + 6)),
        canonical_provenance_column(
            CanonicalProvenanceColumn.STABLE_ROW_ID, CanonicalColumnPosition(trailing_start + 7)
        ),
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
    label_columns=(ColumnName(EdgeCanonicalColumn.ATTACK_LABEL), ColumnName(EdgeCanonicalColumn.ATTACK_TYPE)),
    provenance_columns=EDGE_PROVENANCE_COLUMNS,
    physical_schema=PhysicalSchemaText(
        EDGE_ARROW_SCHEMA.to_string(show_field_metadata=True, show_schema_metadata=True)
    ),
)


def benign_sensor_group(path: Path) -> EdgeSensorGroup:
    if path.suffix != EdgeArtifactSuffix.CSV:
        raise ValueError("unrecognized Edge benign sensor source")
    try:
        group = EdgeSensorGroup(path.parent.name)
    except ValueError as error:
        raise ValueError("unrecognized Edge benign sensor source") from error
    if path.stem != group:
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
