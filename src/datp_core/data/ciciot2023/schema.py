from enum import StrEnum
from pathlib import Path

import pyarrow as pa

from datp_core.core.identifiers import ColumnName, DatasetId, PhysicalSchemaText, RawSourceFilename
from datp_core.core.numeric import CanonicalColumnPosition, ClientCount
from datp_core.data.contracts import (
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalProvenanceColumn,
    CanonicalSchema,
    ColumnLogicalType,
    ModelInputEligibilityPolicy,
)
from datp_core.data.materialization import (
    canonical_provenance_arrow_field,
    canonical_provenance_column,
)


class CICIoT2023Column(StrEnum):
    RAW_LABEL = "raw_label"
    LABEL = "label"
    RATE = "rate"
    MODEL_INPUT_ELIGIBLE = "model_input_eligible"


class CICIoT2023RawColumn(StrEnum):
    HEADER_LENGTH = "Header_Length"
    PROTOCOL_TYPE = "Protocol Type"
    TIME_TO_LIVE = "Time_To_Live"
    RATE = "Rate"
    FIN_FLAG_NUMBER = "fin_flag_number"
    SYN_FLAG_NUMBER = "syn_flag_number"
    RST_FLAG_NUMBER = "rst_flag_number"
    PSH_FLAG_NUMBER = "psh_flag_number"
    ACK_FLAG_NUMBER = "ack_flag_number"
    ECE_FLAG_NUMBER = "ece_flag_number"
    CWR_FLAG_NUMBER = "cwr_flag_number"
    ACK_COUNT = "ack_count"
    SYN_COUNT = "syn_count"
    FIN_COUNT = "fin_count"
    RST_COUNT = "rst_count"
    HTTP = "HTTP"
    HTTPS = "HTTPS"
    DNS = "DNS"
    TELNET = "Telnet"
    SMTP = "SMTP"
    SSH = "SSH"
    IRC = "IRC"
    TCP = "TCP"
    UDP = "UDP"
    DHCP = "DHCP"
    ARP = "ARP"
    ICMP = "ICMP"
    IGMP = "IGMP"
    IPV = "IPv"
    LLC = "LLC"
    TOT_SUM = "Tot sum"
    MIN = "Min"
    MAX = "Max"
    AVG = "AVG"
    STD = "Std"
    TOT_SIZE = "Tot size"
    IAT = "IAT"
    NUMBER = "Number"
    VARIANCE = "Variance"
    LABEL = "Label"


class CICIoT2023NormalizedLabel(StrEnum):
    BENIGN = "BENIGN"
    BACKDOOR_MALWARE = "BACKDOOR_MALWARE"
    BROWSERHIJACKING = "BROWSERHIJACKING"
    COMMANDINJECTION = "COMMANDINJECTION"
    DDOS_ACK_FRAGMENTATION = "DDOS-ACK_FRAGMENTATION"
    DDOS_HTTP_FLOOD = "DDOS-HTTP_FLOOD"
    DDOS_ICMP_FLOOD = "DDOS-ICMP_FLOOD"
    DDOS_ICMP_FRAGMENTATION = "DDOS-ICMP_FRAGMENTATION"
    DDOS_PSHACK_FLOOD = "DDOS-PSHACK_FLOOD"
    DDOS_RSTFINFLOOD = "DDOS-RSTFINFLOOD"
    DDOS_SLOWLORIS = "DDOS-SLOWLORIS"
    DDOS_SYNONYMOUSIP_FLOOD = "DDOS-SYNONYMOUSIP_FLOOD"
    DDOS_SYN_FLOOD = "DDOS-SYN_FLOOD"
    DDOS_TCP_FLOOD = "DDOS-TCP_FLOOD"
    DDOS_UDP_FLOOD = "DDOS-UDP_FLOOD"
    DDOS_UDP_FRAGMENTATION = "DDOS-UDP_FRAGMENTATION"
    DICTIONARYBRUTEFORCE = "DICTIONARYBRUTEFORCE"
    DNS_SPOOFING = "DNS_SPOOFING"
    DOS_HTTP_FLOOD = "DOS-HTTP_FLOOD"
    DOS_SYN_FLOOD = "DOS-SYN_FLOOD"
    DOS_TCP_FLOOD = "DOS-TCP_FLOOD"
    DOS_UDP_FLOOD = "DOS-UDP_FLOOD"
    MIRAI_GREETH_FLOOD = "MIRAI-GREETH_FLOOD"
    MIRAI_GREIP_FLOOD = "MIRAI-GREIP_FLOOD"
    MIRAI_UDPPLAIN = "MIRAI-UDPPLAIN"
    MITM_ARPSPOOFING = "MITM-ARPSPOOFING"
    RECON_HOSTDISCOVERY = "RECON-HOSTDISCOVERY"
    RECON_OSSCAN = "RECON-OSSCAN"
    RECON_PINGSWEEP = "RECON-PINGSWEEP"
    RECON_PORTSCAN = "RECON-PORTSCAN"
    SQLINJECTION = "SQLINJECTION"
    UPLOADING_ATTACK = "UPLOADING_ATTACK"
    VULNERABILITYSCAN = "VULNERABILITYSCAN"
    XSS = "XSS"


class CICIoT2023EligibilityReason(StrEnum):
    MISSING_OR_UNRECOGNIZED_LABEL = "missing_or_unrecognized_label"
    NONFINITE_FEATURE = "nonfinite_feature"


class CICIoT2023AuditField(StrEnum):
    TOTAL_ROWS = "total_rows"
    MISSING_OR_UNRECOGNIZED_LABELS = "missing_or_unrecognized_labels"
    NONFINITE_FEATURE_ROWS = "nonfinite_feature_rows"
    ELIGIBLE_ROWS = "eligible_rows"
    INFINITE_RATES = "infinite_rates"
    EMPTY_RATES = "empty_rates"


class CICIoT2023ArtifactName(StrEnum):
    MERGED_CSV_DIRECTORY = "MERGED_CSV"
    MERGED_FILE_PREFIX = "Merged"
    CSV_SUFFIX = ".csv"


CICIOT2023_AUDITED_FILE_CLIENT_COUNT = ClientCount(63)


CICIOT2023_RAW_COLUMNS: tuple[CICIoT2023RawColumn, ...] = tuple(CICIoT2023RawColumn)
CICIOT2023_FEATURE_COLUMNS: tuple[CICIoT2023RawColumn, ...] = CICIOT2023_RAW_COLUMNS[:-1]
CICIOT2023_LABEL_COLUMN = CICIoT2023RawColumn.LABEL
CICIOT2023_LABELS: frozenset[str] = frozenset(label.value for label in CICIoT2023NormalizedLabel)


def canonical_name(raw_name: CICIoT2023RawColumn) -> ColumnName:
    return ColumnName(raw_name.value.lower().replace(" ", "_").replace("-", "_"))


CICIOT2023_CANONICAL_FEATURE_COLUMNS: tuple[ColumnName, ...] = tuple(
    canonical_name(column) for column in CICIOT2023_FEATURE_COLUMNS
)
CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY = ModelInputEligibilityPolicy(
    dataset=DatasetId.CICIOT2023,
    label_column=ColumnName(CICIoT2023Column.LABEL),
    feature_columns=CICIOT2023_CANONICAL_FEATURE_COLUMNS,
    exclusion_reasons=(
        CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL,
        CICIoT2023EligibilityReason.NONFINITE_FEATURE,
    ),
)
CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN = CICIoT2023Column.MODEL_INPUT_ELIGIBLE
CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS: tuple[ColumnName, ...] = (
    *(ColumnName(reason) for reason in CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY.exclusion_reasons),
    ColumnName(CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN),
)


def _canonical_columns() -> tuple[CanonicalColumn, ...]:
    feature_columns = tuple(
        CanonicalColumn(
            canonical_name(column),
            ColumnName(column),
            ColumnLogicalType.FLOAT64,
            CanonicalColumnRole.FEATURE,
            True,
            CanonicalColumnPosition(position),
        )
        for position, column in enumerate(CICIOT2023_FEATURE_COLUMNS)
    )
    label_position = len(feature_columns)
    label_columns = (
        CanonicalColumn(
            ColumnName(CICIoT2023Column.RAW_LABEL),
            ColumnName(CICIOT2023_LABEL_COLUMN),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(label_position),
        ),
        CanonicalColumn(
            ColumnName(CICIoT2023Column.LABEL),
            ColumnName(CICIOT2023_LABEL_COLUMN),
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(label_position + 1),
        ),
    )
    evidence_position = label_position + len(label_columns)
    evidence_columns = tuple(
        CanonicalColumn(
            column,
            ColumnName("declared model-input eligibility policy"),
            ColumnLogicalType.BOOL,
            CanonicalColumnRole.RAW_EVIDENCE,
            True,
            CanonicalColumnPosition(evidence_position + index),
        )
        for index, column in enumerate(CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS)
    )
    provenance_position = evidence_position + len(evidence_columns)
    provenance_columns = tuple(
        canonical_provenance_column(column, CanonicalColumnPosition(provenance_position + index))
        for index, column in enumerate(CanonicalProvenanceColumn)
    )
    return feature_columns + label_columns + evidence_columns + provenance_columns


CICIOT2023_CANONICAL_COLUMNS = _canonical_columns()
CICIOT2023_ARROW_SCHEMA = pa.schema(
    tuple(pa.field(column, pa.float64(), nullable=True) for column in CICIOT2023_CANONICAL_FEATURE_COLUMNS)
    + (
        pa.field(CICIoT2023Column.RAW_LABEL, pa.large_string()),
        pa.field(CICIoT2023Column.LABEL, pa.large_string()),
        *(pa.field(column, pa.bool_(), nullable=True) for column in CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS),
        *(canonical_provenance_arrow_field(column) for column in CanonicalProvenanceColumn),
    )
)
CICIOT2023_SCHEMA = CanonicalSchema(
    dataset=DatasetId.CICIOT2023,
    columns=CICIOT2023_CANONICAL_COLUMNS,
    feature_columns=CICIOT2023_CANONICAL_FEATURE_COLUMNS,
    label_columns=(ColumnName(CICIoT2023Column.RAW_LABEL), ColumnName(CICIoT2023Column.LABEL)),
    provenance_columns=tuple(ColumnName(column) for column in CanonicalProvenanceColumn),
    physical_schema=PhysicalSchemaText(
        CICIOT2023_ARROW_SCHEMA.to_string(show_field_metadata=True, show_schema_metadata=True)
    ),
)


def is_accepted_merged_source(path_name: RawSourceFilename) -> bool:
    prefix = CICIoT2023ArtifactName.MERGED_FILE_PREFIX
    suffix = CICIoT2023ArtifactName.CSV_SUFFIX
    numeric_identifier = path_name[len(prefix) : -len(suffix)]
    return path_name.startswith(prefix) and path_name.endswith(suffix) and numeric_identifier.isdigit()


def source_relative_path(path: Path) -> Path:
    if path.parent.name != CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY:
        raise ValueError("CICIoT2023 sources must remain in the merged-file directory")
    return Path(path.parent.name, path.name)


def excluded_source_relative_path(path: Path) -> Path:
    return Path(path.parent.name, path.name)
