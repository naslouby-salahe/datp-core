from enum import StrEnum


class SourceTrafficLabel(StrEnum):
    BENIGN = "benign"
    GAFGYT = "gafgyt"
    MIRAI = "mirai"
