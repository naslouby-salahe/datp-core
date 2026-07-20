"""Resolver translating authored Pydantic configuration models into strongly-typed domain records."""

from __future__ import annotations

from pathlib import Path

from datp_core.config.yaml_loader import load_experiments_catalogue, load_protocols_config
from datp_core.domain.catalogue import (
    AnalysisSpecRecord,
    CheckpointProfileRecord,
    EvaluationSpecRecord,
    EvidenceRole,
    ExperimentRecord,
    PopulationRecord,
    ResolvedCatalogue,
    RunRequirement,
    SeedCohortRecord,
    TrainingProfileRecord,
)
from datp_core.domain.fingerprints import compute_fingerprint
from datp_core.domain.identifiers import (
    CheckpointProfileId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    ExperimentId,
    MetricBundleId,
    PopulationId,
    SeedCohortId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.domain.values import PositiveFloat, PositiveInt, Seed, TypedDomainRegistry


def resolve_catalogue(
    experiments_path: Path = Path("configs/experiments.yaml"),
    protocols_path: Path = Path("configs/protocols.yaml"),
) -> ResolvedCatalogue:
    authored_experiments = load_experiments_catalogue(experiments_path)
    authored_protocols = load_protocols_config(protocols_path)

    # 1. Resolve populations
    populations_dict: dict[PopulationId, PopulationRecord] = {}
    for pop_key, pop_cfg in authored_experiments.study_populations.items():
        pop_id = PopulationId(value=pop_key)
        populations_dict[pop_id] = PopulationRecord(
            identifier=pop_id,
            dataset_id=DatasetId(value=pop_cfg.dataset),
            setup_id=DatasetSetupId(value=pop_cfg.setup),
            metric_bundle_id=MetricBundleId(value=pop_cfg.metric_bundle),
        )
    populations_reg = TypedDomainRegistry(_items=populations_dict)

    # 2. Resolve training profiles
    training_dict: dict[TrainingProfileId, TrainingProfileRecord] = {}
    for tp_key, tp_cfg in authored_protocols.training_profiles.items():
        tp_id = TrainingProfileId(value=tp_key)
        training_dict[tp_id] = TrainingProfileRecord(
            identifier=tp_id,
            training_loss=str(tp_cfg.get("reconstruction_loss", "mse")),
            optimizer_type=str(tp_cfg.get("optimizer", "adam_default")),
            learning_rate=PositiveFloat(float(tp_cfg.get("learning_rate", 0.001))),
            max_rounds=PositiveInt(int(tp_cfg.get("rounds", 100))),
            local_epochs=PositiveInt(int(tp_cfg.get("local_epochs", 1))),
        )
    training_reg = TypedDomainRegistry(_items=training_dict)

    # 3. Resolve checkpoint profiles
    checkpoint_dict: dict[CheckpointProfileId, CheckpointProfileRecord] = {}
    for cp_key, cp_cfg in authored_protocols.checkpoint_profiles.items():
        cp_id = CheckpointProfileId(value=cp_key)
        checkpoint_dict[cp_id] = CheckpointProfileRecord(
            identifier=cp_id,
            strategy=str(cp_cfg.get("selection_strategy", "terminal_round")),
            selection_metric=cp_cfg.get("metric_name"),
        )
    checkpoint_reg = TypedDomainRegistry(_items=checkpoint_dict)

    # 4. Resolve seed cohorts
    seed_dict: dict[SeedCohortId, SeedCohortRecord] = {}
    for sc_key, sc_cfg in authored_protocols.seed_cohorts.items():
        sc_id = SeedCohortId(value=sc_key)
        raw_seeds = sc_cfg.get("seeds", list(range(sc_cfg.get("paired_seed_count", 10))))
        seeds_tuple = tuple(Seed(int(s)) for s in raw_seeds)
        seed_dict[sc_id] = SeedCohortRecord(
            identifier=sc_id,
            paired_seed_count=PositiveInt(len(seeds_tuple)),
            seeds=seeds_tuple,
        )
    seed_reg = TypedDomainRegistry(_items=seed_dict)

    # 5. Resolve experiments
    experiments_dict: dict[ExperimentId, ExperimentRecord] = {}
    for exp_cfg in authored_experiments.experiments:
        exp_id = ExperimentId(value=exp_cfg.name)
        evals = tuple(
            EvaluationSpecRecord(
                label=e.label,
                threshold_policy_id=ThresholdPolicyId(value=e.threshold_policy),
            )
            for e in exp_cfg.evaluations
        )
        analyses = tuple(
            AnalysisSpecRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
            )
            for a in exp_cfg.analyses
        )
        experiments_dict[exp_id] = ExperimentRecord(
            identifier=exp_id,
            display_name=exp_cfg.display_name,
            evidence_role=EvidenceRole(exp_cfg.evidence_role),
            run_requirement=RunRequirement(exp_cfg.run_requirement),
            population_ids=tuple(PopulationId(value=p) for p in exp_cfg.populations),
            training_profile_id=TrainingProfileId(value=exp_cfg.training_profile),
            checkpoint_profile_id=CheckpointProfileId(value=exp_cfg.checkpoint_profile),
            seed_cohort_id=SeedCohortId(value=exp_cfg.seed_cohort),
            eligibility_policy_id=EligibilityPolicyId(value=exp_cfg.eligibility_policy),
            prerequisite_ids=tuple(
                ExperimentId(value=p["experiment"]) if isinstance(p, dict) else ExperimentId(value=str(p))
                for p in exp_cfg.prerequisites
            ),
            evaluations=evals,
            analyses=analyses,
        )
    experiments_reg = TypedDomainRegistry(_items=experiments_dict)

    fingerprint = compute_fingerprint(
        {
            "populations": sorted([str(k) for k in populations_dict.keys()]),
            "experiments": sorted([str(k) for k in experiments_dict.keys()]),
            "training_profiles": sorted([str(k) for k in training_dict.keys()]),
            "checkpoint_profiles": sorted([str(k) for k in checkpoint_dict.keys()]),
            "seed_cohorts": sorted([str(k) for k in seed_dict.keys()]),
        }
    )

    return ResolvedCatalogue(
        schema_version=PositiveInt(1),
        populations=populations_reg,
        experiments=experiments_reg,
        training_profiles=training_reg,
        checkpoint_profiles=checkpoint_reg,
        seed_cohorts=seed_reg,
        fingerprint=fingerprint,
    )
