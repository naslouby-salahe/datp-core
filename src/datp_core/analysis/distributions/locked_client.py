"""Locked-client distribution analysis: distribution-mechanism reads specialized to a single
identity-locked client."""

from __future__ import annotations

from datp_core.analysis.distributions.mechanism import distribution_seed_result
from datp_core.analysis.distributions.models import LockedClientDistributionAnalysisResult
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.core.identifiers import ExperimentId
from datp_core.core.seeding import Seed
from datp_core.experiments import ExperimentRecord, LockedClientDistributionAnalysisRecord


def analyze_locked_client_distribution(
    analysis: LockedClientDistributionAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    experiment_id: ExperimentId,
) -> LockedClientDistributionAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(
            experiment,
            seed.value,
            analysis.source_evaluations,
            experiment_id,
            analysis.locked_client_identifier,
            repository=repository,
        )
        for seed in seeds
    )
    return LockedClientDistributionAnalysisResult(
        analysis_label=analysis.label,
        locked_client_identifier=analysis.locked_client_identifier,
        produced_fields=analysis.produced_fields,
        seed_results=seed_results,
    )


__all__ = ["analyze_locked_client_distribution"]
