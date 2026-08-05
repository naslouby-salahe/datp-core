"""Bounded external and applicability-boundary campaign execution."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, PopulationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed
from datp_core.pipeline.campaign_execution import build_campaign, execute_campaign
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.pipeline.runner import ExperimentOutputStore, StageRunner
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.runtime import OUTPUTS_ROOT


class BoundedExternalPlanningReason(StrEnum):
    EDGE_BENIGN_EQUITY_PREREQUISITES = (
        "the external-validation entry point supplies the audited Edge benign-equity prerequisites"
    )
    CICIOT_FILE_CLIENT_PREREQUISITES = (
        "the applicability-boundary entry point supplies the audited CICIoT2023 file-client prerequisites"
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class BoundedExternalSeedResult:
    experiment: ExperimentId
    evidence_role: EvidenceRole
    population: PopulationId
    partition_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


def run_external_validation_seed(partition_seed: Seed) -> BoundedExternalSeedResult:
    return _run_bounded_external_seed(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        partition_seed=partition_seed,
        reason=BoundedExternalPlanningReason.EDGE_BENIGN_EQUITY_PREREQUISITES,
    )


def run_ciciot_boundary_seed(partition_seed: Seed) -> BoundedExternalSeedResult:
    return _run_bounded_external_seed(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        partition_seed=partition_seed,
        reason=BoundedExternalPlanningReason.CICIOT_FILE_CLIENT_PREREQUISITES,
    )


def _run_bounded_external_seed(
    *,
    experiment: ExperimentId,
    partition_seed: Seed,
    reason: BoundedExternalPlanningReason,
) -> BoundedExternalSeedResult:
    declaration = _bounded_external_declaration(experiment)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=reason.value,
            ),
        ),
    )
    campaign = build_campaign(plan)
    if not campaign.entries:
        raise ScientificContractError(
            "bounded external planning produced no executable coordinates",
            subject=declaration.id,
        )
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=StageRunner(),
        output_store=ExperimentOutputStore(),
        output_root=OUTPUTS_ROOT,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(
            f"bounded external execution did not complete: {blocked}",
            subject=declaration.id,
        )
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return BoundedExternalSeedResult(
        experiment=declaration.id,
        evidence_role=declaration.role,
        population=declaration.population,
        partition_seed=partition_seed,
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )


def _bounded_external_declaration(experiment: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment)
    if len(matches) != 1:
        raise ScientificContractError(
            "the bounded external experiment must be declared exactly once",
            subject=experiment,
        )
    declaration = matches[0]
    if declaration.role not in (
        EvidenceRole.EXTERNAL_VALIDATION,
        EvidenceRole.APPLICABILITY_BOUNDARY,
    ):
        raise ScientificContractError(
            "bounded external execution accepts only external-validation or applicability-boundary evidence",
            subject=declaration.role,
        )
    return declaration
