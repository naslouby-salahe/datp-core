"""External benign-equity campaign execution."""

from dataclasses import dataclass

from datp_core.domain.enums import ExperimentId, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed
from datp_core.pipeline.campaign_execution import build_campaign, execute_campaign
from datp_core.pipeline.planning import expand_experiment_plan
from datp_core.pipeline.runner import ExperimentOutputStore, StageRunner
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.runtime import OUTPUTS_ROOT


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalValidationSeedResult:
    partition_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


def run_external_validation_seed(partition_seed: Seed) -> ExternalValidationSeedResult:
    declaration = _external_validation_declaration()
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
    )
    campaign = build_campaign(plan)
    if not campaign.entries:
        raise ScientificContractError("external-validation planning produced no executable coordinates")
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=StageRunner(),
        output_store=ExperimentOutputStore(),
        output_root=OUTPUTS_ROOT,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(f"external validation did not complete: {blocked}")
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return ExternalValidationSeedResult(
        partition_seed=partition_seed,
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )


def _external_validation_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION)
    if len(matches) != 1:
        raise ScientificContractError("the external-validation experiment must be declared exactly once")
    return matches[0]
