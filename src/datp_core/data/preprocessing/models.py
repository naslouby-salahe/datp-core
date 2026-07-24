"""Normalization models and evidence."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class NormalizationFeatureStatistics:
    feature: str
    location: float
    scale: float

    def as_projection(self) -> dict[str, float | str]:
        return {"feature": self.feature, "location": self.location, "scale": self.scale}


@define(frozen=True, slots=True, kw_only=True)
class NormalizationScopeStatistics:
    client_id: str | None
    features: tuple[NormalizationFeatureStatistics, ...]

    def as_projection(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "features": [feature.as_projection() for feature in self.features],
        }


@define(frozen=True, slots=True, kw_only=True)
class NormalizationEvidence:
    strategy: str
    scope: str
    feature_columns: tuple[str, ...]
    fitted_statistics: tuple[NormalizationScopeStatistics, ...]

    def encode(self) -> bytes:
        import json

        return json.dumps(
            {
                "schema_version": 1,
                "strategy": self.strategy,
                "scope": self.scope,
                "feature_columns": self.feature_columns,
                "fitted_statistics": [statistics.as_projection() for statistics in self.fitted_statistics],
            },
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
