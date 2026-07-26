"""Resolution of authored statistical-analysis profiles."""

from __future__ import annotations

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.statistical_profiles import StatisticalMethod, StatisticalProfileRecord
from datp_core.core.identifiers import StatisticalProfileId
from datp_core.core.numbers import PositiveInt, Probability


def resolve_statistical_profiles(
    authored: AuthoredProtocolsConfig,
) -> dict[StatisticalProfileId, StatisticalProfileRecord]:
    statistical_dict: dict[StatisticalProfileId, StatisticalProfileRecord] = {}
    for profile_key, profile_cfg in authored.statistical_profiles.items():
        minimum_units = (
            profile_cfg.minimum_paired_units
            if profile_cfg.minimum_paired_units is not None
            else profile_cfg.minimum_units
        )
        profile_id = StatisticalProfileId(profile_key)
        statistical_dict[profile_id] = StatisticalProfileRecord(
            identifier=profile_id,
            method=(StatisticalMethod(profile_cfg.method)
                    if profile_cfg.method is not None else None),
            confidence_level=(
                Probability(
                    profile_cfg.confidence_level) if profile_cfg.confidence_level is not None else None
            ),
            resample_count=(
                PositiveInt(
                    profile_cfg.resample_count) if profile_cfg.resample_count is not None else None
            ),
            minimum_units=PositiveInt(minimum_units) if minimum_units is not None else None,
        )
    return statistical_dict
