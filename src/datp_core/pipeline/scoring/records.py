"""Pipeline-owned persisted score-frame publication records."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.values import Checksum, FeatureCount, RowCount


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistedScoreFrame:
    path: Path
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount
