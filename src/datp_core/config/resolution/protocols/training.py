"""Resolution of model architecture, optimizer, batching, determinism, seed cohort, checkpoint,
training profile, and normalization-strategy records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.authored.protocols.training import DeterminismProfileConfig
from datp_core.config.errors import ConfigurationError
from datp_core.core.identifiers import CheckpointProfileId, NormalizationStrategyId, SeedCohortId, TrainingProfileId
from datp_core.core.numbers import NonNegativeFloat, PositiveFloat, PositiveInt
from datp_core.core.seeding import Seed
from datp_core.data.contracts import NormalizationStrategyRecord
from datp_core.learning.contracts.architecture import ModelArchitectureRecord
from datp_core.learning.contracts.checkpoints import (
    CheckpointConvergenceRecord,
    CheckpointProfileRecord,
    CheckpointSelectionRecord,
)
from datp_core.learning.contracts.enums import (
    CheckpointAuthorization,
    PersonalizationStrategy,
    TrainingParticipation,
    TrainingProfileKind,
)
from datp_core.learning.contracts.optimization import BatchingRecord, OptimizerRecord
from datp_core.learning.contracts.seeds import SeedCohortRecord
from datp_core.learning.contracts.training import FederationProfileRecord, TrainingProfileRecord


class SeedNamespaceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    components: tuple[str, ...]


class ProtocolDeterminismRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    """Protocols.yaml's own seed/determinism contract (distinct from runtime.yaml's execution determinism)."""

    seed_domains: tuple[str, ...]
    partition_seed_independent_of_training_seeds: bool
    checkpoint_selection_uses_no_stochastic_seed: bool
    derived_seed_digest_bytes: PositiveInt
    seed_namespaces: dict[str, SeedNamespaceRecord]
    resolved_seeds_required_in_manifests: tuple[str, ...]

    @property
    def calibration_subsample_namespace(self) -> SeedNamespaceRecord:
        """Seed namespace for deterministic calibration subsampling."""
        namespace = self.seed_namespaces.get("calibration_subsample")
        if namespace is None:
            raise ValueError("Missing seed namespace 'calibration_subsample' in protocol determinism")
        return namespace


def resolve_training_profiles(authored: AuthoredProtocolsConfig) -> dict[TrainingProfileId, TrainingProfileRecord]:
    training_dict: dict[TrainingProfileId, TrainingProfileRecord] = {}
    for tp_key, tp_cfg in authored.training_profiles.items():
        tp_id = TrainingProfileId(tp_key)
        training_dict[tp_id] = TrainingProfileRecord(
            identifier=tp_id,
            kind=TrainingProfileKind(tp_cfg.kind),
            model_architecture_id=tp_cfg.model_architecture,
            optimizer_id=tp_cfg.optimizer,
            batching_profile_id=tp_cfg.batching,
            local_epochs=(PositiveInt(tp_cfg.local_epochs) if tp_cfg.local_epochs is not None else None),
            participation=TrainingParticipation(tp_cfg.participation) if tp_cfg.participation else None,
            checkpoint_authorization=CheckpointAuthorization(tp_cfg.checkpoint_authorization),
            personalization=PersonalizationStrategy(tp_cfg.personalization) if tp_cfg.personalization else None,
            personalized_local_epochs=(
                PositiveInt(tp_cfg.personalized_local_epochs) if tp_cfg.personalized_local_epochs is not None else None
            ),
            personalization_parameter_grid=(
                tuple(tp_cfg.personalization_parameter_grid)
                if tp_cfg.personalization_parameter_grid is not None
                else None
            ),
            proximal_objective=tp_cfg.proximal_objective,
            mu_grid=tuple(tp_cfg.mu_grid) if tp_cfg.mu_grid is not None else None,
            mu_zero_forbidden_as_a_fedprox_condition=tp_cfg.mu_zero_forbidden_as_a_fedprox_condition,
            federation=(
                FederationProfileRecord(
                    fraction_fit=tp_cfg.federation.fraction_fit,
                    fraction_evaluate=tp_cfg.federation.fraction_evaluate,
                    minimum_fit_clients=PositiveInt(tp_cfg.federation.minimum_fit_clients),
                    minimum_evaluate_clients=PositiveInt(tp_cfg.federation.minimum_evaluate_clients),
                    minimum_available_clients=PositiveInt(tp_cfg.federation.minimum_available_clients),
                )
                if tp_cfg.federation is not None
                else None
            ),
        )
    return training_dict


def resolve_checkpoint_profiles(
    authored: AuthoredProtocolsConfig,
) -> dict[CheckpointProfileId, CheckpointProfileRecord]:
    checkpoint_dict: dict[CheckpointProfileId, CheckpointProfileRecord] = {}
    for cp_key, cp_cfg in authored.checkpoint_profiles.items():
        cp_id = CheckpointProfileId(cp_key)
        selected_rounds = cp_cfg.rounds if cp_cfg.rounds is not None else cp_cfg.epochs
        total_rounds = cp_cfg.total_rounds if cp_cfg.total_rounds is not None else cp_cfg.total_epochs
        if total_rounds is None:
            raise ConfigurationError(f"Checkpoint profile '{cp_key}' has no total rounds or epochs")
        selection_record = CheckpointSelectionRecord(
            rule=cp_cfg.selection.rule,
            tie_break=cp_cfg.selection.tie_break,
            scope=cp_cfg.selection.scope,
            aggregation=cp_cfg.selection.aggregation,
            selected_round_application_scope=cp_cfg.selection.selected_round_application_scope,
            selection_granularity=cp_cfg.selection.selection_granularity,
            forbidden_selectors=tuple(cp_cfg.selection.forbidden_selectors or ()),
        )
        convergence_record = (
            CheckpointConvergenceRecord(
                metric=cp_cfg.convergence.metric,
                rounds_initial=PositiveInt(cp_cfg.convergence.rounds_initial),
                rule=cp_cfg.convergence.rule,
                formula=cp_cfg.convergence.formula,
                zero_start_loss_behavior=cp_cfg.convergence.zero_start_loss_behavior,
                tolerance=PositiveFloat(cp_cfg.convergence.tolerance),
                window_rounds=PositiveInt(cp_cfg.convergence.window_rounds),
                window=cp_cfg.convergence.window,
                qualification=cp_cfg.convergence.qualification,
                no_qualifying_round_behavior=cp_cfg.convergence.no_qualifying_round_behavior,
            )
            if cp_cfg.convergence is not None
            else None
        )
        checkpoint_dict[cp_id] = CheckpointProfileRecord(
            identifier=cp_id,
            total_rounds=PositiveInt(total_rounds),
            selected_rounds=tuple(PositiveInt(round_number) for round_number in (selected_rounds or ())),
            early_stopping=cp_cfg.early_stopping,
            selection_rule=cp_cfg.selection.rule,
            selection=selection_record,
            convergence=convergence_record,
            checkpoint_save_policy=cp_cfg.checkpoint_save_policy,
        )
    return checkpoint_dict


def resolve_seed_cohorts(authored: AuthoredProtocolsConfig) -> dict[SeedCohortId, SeedCohortRecord]:
    seed_dict: dict[SeedCohortId, SeedCohortRecord] = {}
    for sc_key, sc_cfg in authored.seed_cohorts.items():
        sc_id = SeedCohortId(sc_key)
        seeds_tuple = tuple(Seed(int(s)) for s in sc_cfg.training_seeds)
        seed_dict[sc_id] = SeedCohortRecord(
            identifier=sc_id,
            paired_seed_count=PositiveInt(len(seeds_tuple)),
            training_seeds=seeds_tuple,
            bootstrap_analysis_seed=Seed(sc_cfg.bootstrap_analysis_seed),
            analysis_seed_model=sc_cfg.analysis_seed_model,
        )
    return seed_dict


def resolve_model_architectures(authored: AuthoredProtocolsConfig) -> dict[str, ModelArchitectureRecord]:
    return {
        key: ModelArchitectureRecord(
            identifier=key,
            kind=m.kind,
            hidden_dims=tuple(PositiveInt(dim) for dim in m.hidden_dims),
            bottleneck_dim=m.bottleneck_dim,
            activation=m.activation,
            activation_placement=m.activation_placement,
            output_activation=m.output_activation,
            normalization_layers=m.normalization_layers,
            bias=m.bias,
            reconstruction_objective=m.reconstruction_objective,
            training_loss_reduction=m.training_loss_reduction,
            precision=m.precision,
            input_dimension_resolution=m.input_dimension.resolution,
            input_dimension_declared_per_dataset=m.input_dimension.declared_per_dataset,
            input_dimension_validation=m.input_dimension.validation,
            decoder_construction=m.decoder.construction,
            decoder_final_layer_output_dim=m.decoder.final_layer_output_dim,
            weight_initialization=m.parameter_initialization.weight,
            bias_initialization=m.parameter_initialization.bias,
            initialization_applied_to=m.parameter_initialization.applied_to,
            initialization_seeded_by=m.parameter_initialization.seeded_by,
            anomaly_score_definition=m.anomaly_score.definition,
            anomaly_score_orientation=m.anomaly_score.orientation,
        )
        for key, m in authored.model_architectures.items()
    }


def resolve_optimizers(authored: AuthoredProtocolsConfig) -> dict[str, OptimizerRecord]:
    return {
        key: OptimizerRecord(
            identifier=key,
            optimizer_type=o.optimizer_type,
            learning_rate=PositiveFloat(o.learning_rate),
            beta_1=o.beta_1,
            beta_2=o.beta_2,
            epsilon=PositiveFloat(o.epsilon),
            weight_decay=NonNegativeFloat(o.weight_decay),
            amsgrad=o.amsgrad,
            scheduler=o.scheduler,
            gradient_clipping=o.gradient_clipping,
            state_lifecycle=o.state_lifecycle,
            state_aggregated_by_server=o.state_aggregated_by_server,
        )
        for key, o in authored.optimizers.items()
    }


def resolve_batching_profiles(authored: AuthoredProtocolsConfig) -> dict[str, BatchingRecord]:
    return {
        key: BatchingRecord(
            identifier=key,
            micro_batch_size=PositiveInt(b.micro_batch_size),
            gradient_accumulation_steps=PositiveInt(b.gradient_accumulation_steps),
            effective_batch_size=PositiveInt(b.effective_batch_size),
            shuffle_each_epoch=b.shuffle_each_epoch,
            shuffle_unit=b.shuffle_unit,
            incomplete_final_batch=b.incomplete_final_batch,
            row_ordering_before_shuffle=b.row_ordering_before_shuffle,
            shuffle_seed_namespace=b.shuffle_seed_namespace,
            worker_seed_namespace=b.worker_seed_namespace,
        )
        for key, b in authored.batching.items()
    }


def resolve_normalization_strategies(
    authored: AuthoredProtocolsConfig,
) -> dict[NormalizationStrategyId, NormalizationStrategyRecord]:
    return {
        NormalizationStrategyId(k): NormalizationStrategyRecord(
            identifier=NormalizationStrategyId(k),
            formula=v.formula,
            fitted_statistics=tuple(v.fitted_statistics),
            constant_feature_rule=v.constant_feature_rule,
            out_of_range_transform_values=v.out_of_range_transform_values,
            fit_population=v.fit_population,
            standard_deviation_ddof=v.standard_deviation_ddof,
        )
        for k, v in authored.normalization_strategies.items()
    }


def resolve_protocol_determinism(cfg: DeterminismProfileConfig) -> ProtocolDeterminismRecord:
    return ProtocolDeterminismRecord(
        seed_domains=tuple(cfg.seed_domains),
        partition_seed_independent_of_training_seeds=cfg.partition_seed_independent_of_training_seeds,
        checkpoint_selection_uses_no_stochastic_seed=cfg.checkpoint_selection_uses_no_stochastic_seed,
        derived_seed_digest_bytes=PositiveInt(cfg.derived_seed_algorithm["digest_bytes"]),
        seed_namespaces={
            key: SeedNamespaceRecord(key=v.key, components=tuple(v.components))
            for key, v in cfg.seed_namespaces.items()
        },
        resolved_seeds_required_in_manifests=tuple(cfg.resolved_seeds_required_in_manifests),
    )
