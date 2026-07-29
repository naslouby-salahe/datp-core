"""Typed cache request boundary for completed canonical publications."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.datasets.materialization import SourcePathResolver
from datp_core.datasets.materialization import reuse_published_canonical as reuse_materialized_canonical
from datp_core.datasets.models import (
    CanonicalSchema,
    MaterializedDataset,
    ModelInputEligibilityPolicy,
)


@dataclass(frozen=True, slots=True)
class CanonicalReuseRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    canonical_root: Path
    schema: CanonicalSchema
    canonicalization_contract: str
    source_paths: tuple[Path, ...]
    source_path_resolver: SourcePathResolver
    asset_role_type: type[AssetRoleT]
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None


def reuse_published_canonical[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    request: CanonicalReuseRequest[AssetRoleT, EligibilityReasonT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT] | None:
    """Reuse a publication whose schema, policy, source state, and assets remain current."""
    return reuse_materialized_canonical(request)
