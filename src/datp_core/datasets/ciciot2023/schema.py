"""Audited CICIoT2023 merged-file schema."""

from enum import StrEnum
from pathlib import Path

import pyarrow as pa

from datp_core.datasets.contracts import (
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalProvenanceColumn,
    CanonicalSchema,
    ColumnLogicalType,
    ModelInputEligibilityPolicy,
)
from datp_core.datasets.materialization import (
    canonical_provenance_arrow_field,
    canonical_provenance_column,
    canonical_schema_checksum,
)
from datp_core.domain.enums import DatasetId
from datp_core.domain.values import (
    CanonicalColumnPosition,
    ClientCount,
)


class CICIoT2023Column(StrEnum):
    RAW_LABEL = "raw_label"
    LABEL = "label"
    RATE = "rate"
    MODEL_INPUT_ELIGIBLE = "model_input_eligible"


class CICIoT2023RawColumn(StrEnum):
    LABEL = "Label"


class CICIoT2023NormalizedLabel(StrEnum):
    """Normalized label vocabulary retained on the audited merged artifact."""

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


CICIOT2023_RAW_COLUMNS: tuple[str, ...] = tuple(
    (
        "Header_Length,Protocol Type,Time_To_Live,Rate,fin_flag_number,syn_flag_number,rst_flag_number,"
        "psh_flag_number,ack_flag_number,ece_flag_number,cwr_flag_number,ack_count,syn_count,fin_count,"
        "rst_count,HTTP,HTTPS,DNS,Telnet,SMTP,SSH,IRC,TCP,UDP,DHCP,ARP,ICMP,IGMP,IPv,LLC,Tot sum,"
        "Min,Max,AVG,Std,Tot size,IAT,Number,Variance,Label"
    ).split(",")
)
CICIOT2023_FEATURE_COLUMNS: tuple[str, ...] = CICIOT2023_RAW_COLUMNS[:-1]
CICIOT2023_LABEL_COLUMN = CICIoT2023RawColumn.LABEL
CICIOT2023_LABELS: frozenset[str] = frozenset(label.value for label in CICIoT2023NormalizedLabel)


def canonical_name(raw_name: str) -> str:
    return raw_name.lower().replace(" ", "_").replace("-", "_")


CICIOT2023_CANONICAL_FEATURE_COLUMNS: tuple[str, ...] = tuple(
    canonical_name(column) for column in CICIOT2023_FEATURE_COLUMNS
)
CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY = ModelInputEligibilityPolicy(
    dataset=DatasetId.CICIOT2023,
    label_column=CICIoT2023Column.LABEL,
    feature_columns=CICIOT2023_CANONICAL_FEATURE_COLUMNS,
    exclusion_reasons=(
        CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL,
        CICIoT2023EligibilityReason.NONFINITE_FEATURE,
    ),
)
CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN = CICIoT2023Column.MODEL_INPUT_ELIGIBLE
CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS: tuple[str, ...] = (
    *(reason.value for reason in CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY.exclusion_reasons),
    CICIOT2023_MODEL_INPUT_ELIGIBLE_COLUMN,
)
CICIOT2023_PROVENANCE_COLUMNS: tuple[str, ...] = tuple(CanonicalProvenanceColumn)


def _canonical_columns() -> tuple[CanonicalColumn, ...]:
    feature_columns = tuple(
        CanonicalColumn(
            canonical_name(column),
            column,
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
            CICIoT2023Column.RAW_LABEL,
            CICIOT2023_LABEL_COLUMN,
            ColumnLogicalType.STRING,
            CanonicalColumnRole.LABEL,
            True,
            CanonicalColumnPosition(label_position),
        ),
        CanonicalColumn(
            CICIoT2023Column.LABEL,
            CICIOT2023_LABEL_COLUMN,
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
            "declared model-input eligibility policy",
            ColumnLogicalType.BOOL,
            CanonicalColumnRole.RAW_EVIDENCE,
            True,
            CanonicalColumnPosition(evidence_position + index),
        )
        for index, column in enumerate(CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS)
    )
    provenance_position = evidence_position + len(evidence_columns)
    provenance_columns = tuple(
        canonical_provenance_column(column, provenance_position + index)
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
    label_columns=(CICIoT2023Column.RAW_LABEL, CICIoT2023Column.LABEL),
    provenance_columns=CICIOT2023_PROVENANCE_COLUMNS,
    physical_schema=CICIOT2023_ARROW_SCHEMA.to_string(show_field_metadata=True, show_schema_metadata=True),
    checksum=canonical_schema_checksum(DatasetId.CICIOT2023, CICIOT2023_CANONICAL_COLUMNS, CICIOT2023_ARROW_SCHEMA),
)


def is_accepted_merged_source(path_name: str) -> bool:
    prefix = CICIoT2023ArtifactName.MERGED_FILE_PREFIX
    suffix = CICIoT2023ArtifactName.CSV_SUFFIX
    numeric_identifier = path_name[len(prefix) : -len(suffix)]
    return path_name.startswith(prefix) and path_name.endswith(suffix) and numeric_identifier.isdigit()


def source_relative_path(path: Path) -> Path:
    if path.parent.name != CICIoT2023ArtifactName.MERGED_CSV_DIRECTORY:
        raise ValueError("CICIoT2023 sources must remain in the merged-file directory")
    return Path(path.parent.name, path.name)
