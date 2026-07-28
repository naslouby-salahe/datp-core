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
from datp_core.data.contracts.enums import (
    ConstantFeaturePolicy,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
)
from datp_core.data.contracts.materialization import (
    MinMaxNormalizationConfig,
    NormalizationConfig,
    StandardNormalizationConfig,
)
from datp_core.learning.contracts.checkpoints import (
    CheckpointProfile,
    CheckpointSelectionProfile,
    FirstQualifyingConvergenceSelection,
    FixedRoundSelection,
    LowestCalibrationLossSelection,
)
from datp_core.learning.contracts.enums import (
    ActivationKind,
    BiasInitializationKind,
    CheckpointAuthorization,
    CheckpointSavePolicy,
    CheckpointSelectionKind,
    CheckpointTieBreak,
    ModelArchitectureKind,
    NoQualifyingRoundPolicy,
    NormalizationKind,
    OptimizerKind,
    OptimizerStateLifecycle,
    OutputActivationKind,
    ParticipationPolicy,
    PrecisionKind,
    ReconstructionObjective,
    LossReduction,
    SeedAnalysisModel,
    TrainingAlgorithm,
    WeightInitializationKind,
)
from datp_core.learning.contracts.model import (
    AdamOptimizerProfile,
    BatchingProfile,
    DenseAutoencoderProfile,
    GlobalNormGradientClippingProfile,
    LearningDataSchema,
    NoGradientClippingProfile,
    NoSchedulerProfile,
    StepSchedulerProfile,
)
from datp_core.learning.contracts.training import (
    CentralizedTrainingProfile,
    DittoTrainingProfile,
    FedAvgTrainingProfile,
    FedProxTrainingProfile,
    FullParticipationProfile,
    SeedCohortProfile,
)
from datp_core.learning.model.runtime import SeedDerivationProfile, SeedNamespaceProfile, TorchRuntimeProfile

_OBJECTIVE_MAP = {"mse": "mean_squared_error", "mae": "mean_absolute_error", "huber": "huber"}
_REDUCTION_MAP = {
    "mean_over_all_elements_of_the_batch": "mean",
    "sum_over_all_elements_of_the_batch": "sum",
}
_PRECISION_MAP = {"fp32": "float32", "fp64": "float64"}
_WEIGHT_INIT_MAP = {
    "kaiming_uniform_fan_in_leaky_relu_negative_slope_sqrt_5": "kaiming_uniform",
    "xavier_uniform_fan_in_sigmoid_gain_1": "xavier_uniform",
}
_BIAS_INIT_MAP = {"uniform_symmetric_one_over_sqrt_fan_in": "zero"}
_STATE_LIFECYCLE_MAP = {
    "recreated_at_the_start_of_every_local_fit_never_persisted_across_rounds": "reset_each_local_training",
}
_SHUFFLE_MAP = {"true": "each_epoch", "false": "disabled"}
_INCOMPLETE_BATCH_MAP = {"retained_never_dropped": "keep", "dropped_never_retained": "drop"}

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


def resolve_training_profiles(
    authored: AuthoredProtocolsConfig,
) -> dict[
    TrainingProfileId,
    CentralizedTrainingProfile | FedAvgTrainingProfile | FedProxTrainingProfile | DittoTrainingProfile,
]:
    training_dict: dict[
        TrainingProfileId,
        CentralizedTrainingProfile | FedAvgTrainingProfile | FedProxTrainingProfile | DittoTrainingProfile,
    ] = {}
    for tp_key, tp_cfg in authored.training_profiles.items():
        tp_id = TrainingProfileId(tp_key)
        ckpt_auth = CheckpointAuthorization(tp_cfg.checkpoint_authorization)
        local_epochs = tp_cfg.local_epochs or 1
        if tp_cfg.kind == "centralized_pooled_training":
            profile: (
                CentralizedTrainingProfile | FedAvgTrainingProfile | FedProxTrainingProfile | DittoTrainingProfile
            ) = CentralizedTrainingProfile(
                identifier=tp_id,
                model_architecture_id=tp_cfg.model_architecture,
                optimizer_id=tp_cfg.optimizer,
                batching_profile_id=tp_cfg.batching,
                checkpoint_authorization=ckpt_auth,
                algorithm=TrainingAlgorithm.CENTRALIZED,
                local_epochs=local_epochs,
            )
        elif tp_cfg.personalization == "ditto" and tp_cfg.federation is not None:
            profile = DittoTrainingProfile(
                identifier=tp_id,
                model_architecture_id=tp_cfg.model_architecture,
                optimizer_id=tp_cfg.optimizer,
                batching_profile_id=tp_cfg.batching,
                checkpoint_authorization=ckpt_auth,
                algorithm=TrainingAlgorithm.DITTO,
                global_local_epochs=local_epochs,
                personalized_local_epochs=tp_cfg.personalized_local_epochs or 1,
                participation=FullParticipationProfile(
                    policy=ParticipationPolicy.FULL,
                    minimum_available_clients=tp_cfg.federation.minimum_available_clients,
                ),
                personalization_weights=tuple(float(w) for w in (tp_cfg.personalization_parameter_grid or [])),
            )
        elif tp_cfg.kind == "federated_prox_training" and tp_cfg.federation is not None:
            profile = FedProxTrainingProfile(
                identifier=tp_id,
                model_architecture_id=tp_cfg.model_architecture,
                optimizer_id=tp_cfg.optimizer,
                batching_profile_id=tp_cfg.batching,
                checkpoint_authorization=ckpt_auth,
                algorithm=TrainingAlgorithm.FEDPROX,
                local_epochs=local_epochs,
                participation=FullParticipationProfile(
                    policy=ParticipationPolicy.FULL,
                    minimum_available_clients=tp_cfg.federation.minimum_available_clients,
                ),
                proximal_coefficients=tuple(float(mu) for mu in (tp_cfg.mu_grid or [])),
            )
        elif tp_cfg.federation is not None:
            profile = FedAvgTrainingProfile(
                identifier=tp_id,
                model_architecture_id=tp_cfg.model_architecture,
                optimizer_id=tp_cfg.optimizer,
                batching_profile_id=tp_cfg.batching,
                checkpoint_authorization=ckpt_auth,
                algorithm=TrainingAlgorithm.FEDAVG,
                local_epochs=local_epochs,
                participation=FullParticipationProfile(
                    policy=ParticipationPolicy.FULL,
                    minimum_available_clients=tp_cfg.federation.minimum_available_clients,
                ),
            )
        else:
            raise ConfigurationError(f"Training profile '{tp_key}' lacks federation configuration")
        training_dict[tp_id] = profile
    return training_dict


def resolve_checkpoint_profiles(
    authored: AuthoredProtocolsConfig,
) -> dict[CheckpointProfileId, CheckpointProfile]:
    checkpoint_dict: dict[CheckpointProfileId, CheckpointProfile] = {}
    for cp_key, cp_cfg in authored.checkpoint_profiles.items():
        cp_id = CheckpointProfileId(cp_key)
        selected_rounds = cp_cfg.rounds if cp_cfg.rounds is not None else cp_cfg.epochs
        capture_rounds = tuple(int(round_number) for round_number in (selected_rounds or ()))
        total_rounds_val = cp_cfg.total_rounds if cp_cfg.total_rounds is not None else cp_cfg.total_epochs
        if total_rounds_val is None:
            raise ConfigurationError(f"Checkpoint profile '{cp_key}' has no total rounds or epochs")
        rule = cp_cfg.selection.rule
        if "lowest" in rule:
            tie = (
                CheckpointTieBreak.EARLIEST_ROUND
                if "earliest" in (cp_cfg.selection.tie_break or "")
                else CheckpointTieBreak.LATEST_ROUND
            )
            selection: CheckpointSelectionProfile = LowestCalibrationLossSelection(
                kind=CheckpointSelectionKind.LOWEST_CALIBRATION_LOSS,
                tie_break=tie,
            )
        elif "convergence" in rule or "first_qualifying" in rule or "first_historically" in rule:
            convergence = cp_cfg.convergence
            selection = FirstQualifyingConvergenceSelection(
                kind=CheckpointSelectionKind.FIRST_QUALIFYING_CONVERGENCE,
                initial_rounds=(
                    int(convergence.rounds_initial) if convergence is not None else int(50)
                ),
                window_rounds=(int(convergence.window_rounds) if convergence is not None else int(10)),
                relative_loss_tolerance=(
                    float(convergence.tolerance) if convergence is not None else float(1e-4)
                ),
                tie_break=CheckpointTieBreak.EARLIEST_ROUND,
                no_qualifying_round=NoQualifyingRoundPolicy.FINAL_ROUND,
            )
        elif "fixed" in rule:
            selected = capture_rounds[-1] if capture_rounds else int(1)
            selection = FixedRoundSelection(
                kind=CheckpointSelectionKind.FIXED_ROUND,
                selected_round=selected,
            )
        else:
            raise ConfigurationError(f"Unsupported checkpoint selection rule '{rule}' in profile '{cp_key}'")
        checkpoint_dict[cp_id] = CheckpointProfile(
            identifier=cp_id,
            total_rounds=int(total_rounds_val),
            capture_rounds=capture_rounds,
            save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
            selection=selection,
        )
    return checkpoint_dict


def resolve_seed_cohorts(authored: AuthoredProtocolsConfig) -> dict[SeedCohortId, SeedCohortProfile]:
    seed_dict: dict[SeedCohortId, SeedCohortProfile] = {}
    for sc_key, sc_cfg in authored.seed_cohorts.items():
        sc_id = SeedCohortId(sc_key)
        seeds_tuple = tuple(Seed(int(s)) for s in sc_cfg.training_seeds)
        seed_dict[sc_id] = SeedCohortProfile(
            identifier=sc_id,
            paired_seed_count=int(len(seeds_tuple)),
            training_seeds=seeds_tuple,
            bootstrap_analysis_seed=Seed(sc_cfg.bootstrap_analysis_seed),
            analysis_seed_model=SeedAnalysisModel.PAIRED,
        )
    return seed_dict


def resolve_model_architectures(authored: AuthoredProtocolsConfig) -> dict[str, DenseAutoencoderProfile]:
    return {
        key: DenseAutoencoderProfile(
            identifier=key,
            kind=ModelArchitectureKind.DENSE_AUTOENCODER,
            hidden_dimensions=tuple(int(dim) for dim in m.hidden_dims),
            activation=ActivationKind(m.activation),
            output_activation=OutputActivationKind(m.output_activation),
            normalization=NormalizationKind(m.normalization_layers),
            use_bias=m.bias,
            objective=ReconstructionObjective(_OBJECTIVE_MAP.get(m.reconstruction_objective, m.reconstruction_objective)),
            reduction=LossReduction(_REDUCTION_MAP.get(m.training_loss_reduction, m.training_loss_reduction)),
            precision=PrecisionKind(_PRECISION_MAP.get(m.precision, m.precision)),
            weight_initialization=WeightInitializationKind(
                _WEIGHT_INIT_MAP.get(m.parameter_initialization.weight, m.parameter_initialization.weight)
            ),
            bias_initialization=BiasInitializationKind(
                _BIAS_INIT_MAP.get(m.parameter_initialization.bias, m.parameter_initialization.bias)
            ),
        )
        for key, m in authored.model_architectures.items()
    }


def resolve_optimizers(authored: AuthoredProtocolsConfig) -> dict[str, AdamOptimizerProfile]:
    return {
        key: AdamOptimizerProfile(
            identifier=key,
            kind="adam",
            learning_rate=float(o.learning_rate),
            beta_1=o.beta_1,
            beta_2=o.beta_2,
            epsilon=float(o.epsilon),
            weight_decay=float(o.weight_decay),
            amsgrad=o.amsgrad,
            scheduler=(
                NoSchedulerProfile(kind="none")
                if o.scheduler == "none"
                else StepSchedulerProfile(
                    kind="step",
                    step_size_epochs=int(1),
                    gamma=0.9,
                )
            ),
            gradient_clipping=(
                NoGradientClippingProfile(kind="none")
                if o.gradient_clipping == "none"
                else GlobalNormGradientClippingProfile(
                    kind="global_norm",
                    maximum_norm=float(1.0),
                )
            ),
            state_lifecycle="reset_each_local_training",
        )
        for key, o in authored.optimizers.items()
    }


def resolve_batching_profiles(authored: AuthoredProtocolsConfig) -> dict[str, BatchingProfile]:
    return {
        key: BatchingProfile(
            identifier=key,
            micro_batch_size=int(b.micro_batch_size),
            gradient_accumulation_steps=int(b.gradient_accumulation_steps),
            shuffle_policy=_SHUFFLE_MAP.get(str(b.shuffle_each_epoch).lower(), "disabled"),
            incomplete_batch_policy=_INCOMPLETE_BATCH_MAP.get(b.incomplete_final_batch, "keep"),
            accumulation_remainder_policy="step_partial",
            worker_count=0,
            pin_memory=False,
            persistent_workers=False,
        )
        for key, b in authored.batching.items()
    }


def resolve_normalization_strategies(
    authored: AuthoredProtocolsConfig,
) -> dict[NormalizationStrategyId, NormalizationConfig]:
    result: dict[NormalizationStrategyId, NormalizationConfig] = {}
    for k, v in authored.normalization_strategies.items():
        nid = NormalizationStrategyId(k)
        if "per_client" in v.fit_population:
            fit_scope = NormalizationFitScope.PER_CLIENT_TRAIN
        elif "historical" in v.fit_population:
            fit_scope = NormalizationFitScope.HISTORICAL_TRAIN
        else:
            fit_scope = NormalizationFitScope.GLOBAL_TRAIN
        if "min_max" in k:
            result[nid] = MinMaxNormalizationConfig(
                strategy=NormalizationStrategy.MIN_MAX,
                fit_scope=fit_scope,
                constant_feature_policy=ConstantFeaturePolicy.ZERO,
                out_of_range_policy=OutOfRangePolicy.PRESERVE,
            )
        else:
            result[nid] = StandardNormalizationConfig(
                strategy=NormalizationStrategy.STANDARD,
                fit_scope=fit_scope,
                standard_deviation_ddof=int(v.standard_deviation_ddof or 0),
                constant_feature_policy=ConstantFeaturePolicy.ERROR,
                out_of_range_policy=OutOfRangePolicy.PRESERVE,
            )
    return result


def resolve_protocol_determinism(cfg: DeterminismProfileConfig) -> ProtocolDeterminismRecord:
    return ProtocolDeterminismRecord(
        seed_domains=tuple(cfg.seed_domains),
        partition_seed_independent_of_training_seeds=cfg.partition_seed_independent_of_training_seeds,
        checkpoint_selection_uses_no_stochastic_seed=cfg.checkpoint_selection_uses_no_stochastic_seed,
        derived_seed_digest_bytes=int(cfg.derived_seed_algorithm["digest_bytes"]),
        seed_namespaces={
            key: SeedNamespaceRecord(key=v.key, components=tuple(v.components))
            for key, v in cfg.seed_namespaces.items()
        },
        resolved_seeds_required_in_manifests=tuple(cfg.resolved_seeds_required_in_manifests),
    )


def resolve_learning_data_schemas(
    authored: AuthoredProtocolsConfig,
) -> dict[str, LearningDataSchema]:
    """LearningDataSchema records are resolved from dataset materialization config, not protocols.yaml."""
    return {}


def resolve_runtime_profile(authored: AuthoredProtocolsConfig) -> TorchRuntimeProfile:
    """TorchRuntimeProfile must be resolved from runtime.yaml and the active execution profile."""
    raise ConfigurationError(
        "TorchRuntimeProfile cannot be resolved from AuthoredProtocolsConfig alone; "
        "resolve it from AuthoredRuntimeConfig instead"
    )


def resolve_seed_derivation_profile(authored: AuthoredProtocolsConfig) -> SeedDerivationProfile:
    determ = authored.determinism
    ns = determ.seed_namespaces
    return SeedDerivationProfile(
        digest_bytes=int(determ.derived_seed_algorithm["digest_bytes"]),
        model_initialization=SeedNamespaceProfile(
            identifier="model_initialization",
            key=ns["model_initialization"].key,
        ),
        global_dataloader_shuffle=SeedNamespaceProfile(
            identifier="global_dataloader_shuffle",
            key=ns["global_dataloader_shuffle"].key,
        ),
        personalized_dataloader_shuffle=SeedNamespaceProfile(
            identifier="personalized_dataloader_shuffle",
            key=ns["personalized_dataloader_shuffle"].key,
        ),
        worker_initialization=SeedNamespaceProfile(
            identifier="worker_initialization",
            key=ns["worker_initialization"].key,
        ),
    )
