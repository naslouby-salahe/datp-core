"""Tests for learning contract models."""
# pylint: disable=missing-docstring,no-self-use

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp_core.core.identifiers import CheckpointProfileId, SeedCohortId, TrainingProfileId
from datp_core.core.seeding import Seed
from datp_core.data.contracts.enums import SplitMembership
from datp_core.learning.contracts.checkpoints import (
    CheckpointProfile,
    FirstQualifyingConvergenceSelection,
    FixedRoundSelection,
    LowestCalibrationLossSelection,
)
from datp_core.learning.contracts.enums import (
    AccumulationRemainderPolicy,
    ActivationKind,
    BiasInitializationKind,
    CheckpointAuthorization,
    CheckpointSavePolicy,
    CheckpointSelectionKind,
    CheckpointTieBreak,
    GradientClippingKind,
    IncompleteBatchPolicy,
    LossReduction,
    ModelArchitectureKind,
    NoQualifyingRoundPolicy,
    NormalizationKind,
    OptimizerKind,
    OptimizerStateLifecycle,
    OutputActivationKind,
    ParticipationPolicy,
    PrecisionKind,
    ReconstructionObjective,
    SchedulerKind,
    SeedAnalysisModel,
    ShufflePolicy,
    SplitProfileKind,
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
    StandardSplitProfile,
    StepSchedulerProfile,
    TemporalSplitProfile,
)
from datp_core.learning.contracts.training import (
    CentralizedTrainingProfile,
    DittoTrainingProfile,
    FedAvgTrainingProfile,
    FedProxTrainingProfile,
    FullParticipationProfile,
    SeedCohortProfile,
)


# ---------------------------------------------------------------------------
# DenseAutoencoderProfile
# ---------------------------------------------------------------------------


class TestDenseAutoencoderProfile:
    def test_valid_construction(self):
        profile = DenseAutoencoderProfile(
            identifier="test_ae",
            kind=ModelArchitectureKind.DENSE_AUTOENCODER,
            hidden_dimensions=(64, 32, 16),
            activation=ActivationKind.RELU,
            output_activation=OutputActivationKind.IDENTITY,
            normalization=NormalizationKind.BATCH_NORMALIZATION,
            use_bias=True,
            objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
            reduction=LossReduction.MEAN,
            precision=PrecisionKind.FLOAT32,
            weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
            bias_initialization=BiasInitializationKind.ZERO,
        )
        assert profile.identifier == "test_ae"
        assert profile.hidden_dimensions == (64, 32, 16)

    def test_empty_hidden_dimensions_rejected(self):
        with pytest.raises(ValidationError):
            DenseAutoencoderProfile(
                identifier="test_ae",
                kind=ModelArchitectureKind.DENSE_AUTOENCODER,
                hidden_dimensions=(),
                activation=ActivationKind.RELU,
                output_activation=OutputActivationKind.IDENTITY,
                normalization=NormalizationKind.NONE,
                use_bias=True,
                objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
                reduction=LossReduction.MEAN,
                precision=PrecisionKind.FLOAT32,
                weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
                bias_initialization=BiasInitializationKind.ZERO,
            )

    def test_bottleneck_dimension(self):
        profile = DenseAutoencoderProfile(
            identifier="test_ae",
            kind=ModelArchitectureKind.DENSE_AUTOENCODER,
            hidden_dimensions=(64, 32, 16),
            activation=ActivationKind.RELU,
            output_activation=OutputActivationKind.IDENTITY,
            normalization=NormalizationKind.NONE,
            use_bias=True,
            objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
            reduction=LossReduction.MEAN,
            precision=PrecisionKind.FLOAT32,
            weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
            bias_initialization=BiasInitializationKind.ZERO,
        )
        assert profile.bottleneck_dimension == 16

    def test_unknown_fields_rejected(self):
        with pytest.raises(ValidationError):
            DenseAutoencoderProfile(
                identifier="test_ae",
                kind=ModelArchitectureKind.DENSE_AUTOENCODER,
                hidden_dimensions=(64, 32, 16),
                activation=ActivationKind.RELU,
                output_activation=OutputActivationKind.IDENTITY,
                normalization=NormalizationKind.NONE,
                use_bias=True,
                objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
                reduction=LossReduction.MEAN,
                precision=PrecisionKind.FLOAT32,
                weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
                bias_initialization=BiasInitializationKind.ZERO,
                unknown_field="xyz",
            )

    @pytest.mark.parametrize(
        "activation",
        [ActivationKind.RELU, ActivationKind.LEAKY_RELU, ActivationKind.GELU, ActivationKind.ELU],
    )
    def test_various_activations(self, activation):
        profile = DenseAutoencoderProfile(
            identifier="test_ae",
            kind=ModelArchitectureKind.DENSE_AUTOENCODER,
            hidden_dimensions=(32, 16),
            activation=activation,
            output_activation=OutputActivationKind.IDENTITY,
            normalization=NormalizationKind.NONE,
            use_bias=True,
            objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
            reduction=LossReduction.MEAN,
            precision=PrecisionKind.FLOAT32,
            weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
            bias_initialization=BiasInitializationKind.ZERO,
        )
        assert profile.activation == activation

    @pytest.mark.parametrize(
        "normalization",
        [
            NormalizationKind.NONE,
            NormalizationKind.BATCH_NORMALIZATION,
            NormalizationKind.LAYER_NORMALIZATION,
        ],
    )
    def test_various_normalizations(self, normalization):
        profile = DenseAutoencoderProfile(
            identifier="test_ae",
            kind=ModelArchitectureKind.DENSE_AUTOENCODER,
            hidden_dimensions=(32, 16),
            activation=ActivationKind.RELU,
            output_activation=OutputActivationKind.IDENTITY,
            normalization=normalization,
            use_bias=True,
            objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
            reduction=LossReduction.MEAN,
            precision=PrecisionKind.FLOAT32,
            weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
            bias_initialization=BiasInitializationKind.ZERO,
        )
        assert profile.normalization == normalization

    @pytest.mark.parametrize(
        "precision",
        [PrecisionKind.FLOAT32, PrecisionKind.FLOAT64],
    )
    def test_various_precisions(self, precision):
        profile = DenseAutoencoderProfile(
            identifier="test_ae",
            kind=ModelArchitectureKind.DENSE_AUTOENCODER,
            hidden_dimensions=(32, 16),
            activation=ActivationKind.RELU,
            output_activation=OutputActivationKind.IDENTITY,
            normalization=NormalizationKind.NONE,
            use_bias=True,
            objective=ReconstructionObjective.MEAN_SQUARED_ERROR,
            reduction=LossReduction.MEAN,
            precision=precision,
            weight_initialization=WeightInitializationKind.KAIMING_UNIFORM,
            bias_initialization=BiasInitializationKind.ZERO,
        )
        assert profile.precision == precision


# ---------------------------------------------------------------------------
# AdamOptimizerProfile
# ---------------------------------------------------------------------------


class TestAdamOptimizerProfile:
    def test_valid_construction(self):
        scheduler = NoSchedulerProfile(kind=SchedulerKind.NONE)
        gradient_clipping = NoGradientClippingProfile(kind=GradientClippingKind.NONE)
        profile = AdamOptimizerProfile(
            identifier="test_adam",
            kind=OptimizerKind.ADAM,
            learning_rate=0.001,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=1e-8,
            weight_decay=0.0,
            amsgrad=False,
            scheduler=scheduler,
            gradient_clipping=gradient_clipping,
            state_lifecycle=OptimizerStateLifecycle.RESET_EACH_LOCAL_TRAINING,
        )
        assert profile.identifier == "test_adam"

    def test_scheduler_and_gradient_clipping_discriminated(self):
        scheduler = StepSchedulerProfile(
            kind=SchedulerKind.STEP, step_size_epochs=10, gamma=0.5
        )
        gradient_clipping = GlobalNormGradientClippingProfile(
            kind=GradientClippingKind.GLOBAL_NORM, maximum_norm=1.0
        )
        profile = AdamOptimizerProfile(
            identifier="test_adam",
            kind=OptimizerKind.ADAM,
            learning_rate=0.001,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=1e-8,
            weight_decay=1e-5,
            amsgrad=True,
            scheduler=scheduler,
            gradient_clipping=gradient_clipping,
            state_lifecycle=OptimizerStateLifecycle.RESET_EACH_LOCAL_TRAINING,
        )
        assert isinstance(profile.scheduler, StepSchedulerProfile)
        assert isinstance(profile.gradient_clipping, GlobalNormGradientClippingProfile)

    def test_beta_1_must_be_in_0_1_exclusive(self):
        scheduler = NoSchedulerProfile(kind=SchedulerKind.NONE)
        gradient_clipping = NoGradientClippingProfile(kind=GradientClippingKind.NONE)
        with pytest.raises(ValidationError):
            AdamOptimizerProfile(
                identifier="test_adam",
                kind=OptimizerKind.ADAM,
                learning_rate=0.001,
                beta_1=0.0,
                beta_2=0.999,
                epsilon=1e-8,
                weight_decay=0.0,
                amsgrad=False,
                scheduler=scheduler,
                gradient_clipping=gradient_clipping,
                state_lifecycle=OptimizerStateLifecycle.RESET_EACH_LOCAL_TRAINING,
            )

    def test_beta_2_must_be_in_0_1_exclusive(self):
        scheduler = NoSchedulerProfile(kind=SchedulerKind.NONE)
        gradient_clipping = NoGradientClippingProfile(kind=GradientClippingKind.NONE)
        with pytest.raises(ValidationError):
            AdamOptimizerProfile(
                identifier="test_adam",
                kind=OptimizerKind.ADAM,
                learning_rate=0.001,
                beta_1=0.9,
                beta_2=1.0,
                epsilon=1e-8,
                weight_decay=0.0,
                amsgrad=False,
                scheduler=scheduler,
                gradient_clipping=gradient_clipping,
                state_lifecycle=OptimizerStateLifecycle.RESET_EACH_LOCAL_TRAINING,
            )

    def test_missing_required_fields_rejected(self):
        gradient_clipping = NoGradientClippingProfile(kind=GradientClippingKind.NONE)
        with pytest.raises(ValidationError):
            AdamOptimizerProfile(
                identifier="test_adam",
                kind=OptimizerKind.ADAM,
                learning_rate=0.001,
                beta_1=0.9,
                epsilon=1e-8,
                weight_decay=0.0,
                amsgrad=False,
                scheduler=NoSchedulerProfile(kind=SchedulerKind.NONE),
                gradient_clipping=gradient_clipping,
                state_lifecycle=OptimizerStateLifecycle.RESET_EACH_LOCAL_TRAINING,
            )


# ---------------------------------------------------------------------------
# BatchingProfile
# ---------------------------------------------------------------------------


class TestBatchingProfile:
    def test_valid_construction(self):
        profile = BatchingProfile(
            identifier="test_batch",
            micro_batch_size=32,
            gradient_accumulation_steps=4,
            shuffle_policy=ShufflePolicy.EACH_EPOCH,
            incomplete_batch_policy=IncompleteBatchPolicy.KEEP,
            accumulation_remainder_policy=AccumulationRemainderPolicy.STEP_PARTIAL,
            worker_count=2,
            pin_memory=True,
            persistent_workers=True,
        )
        assert profile.identifier == "test_batch"

    def test_effective_batch_size(self):
        profile = BatchingProfile(
            identifier="test_batch",
            micro_batch_size=32,
            gradient_accumulation_steps=4,
            shuffle_policy=ShufflePolicy.EACH_EPOCH,
            incomplete_batch_policy=IncompleteBatchPolicy.KEEP,
            accumulation_remainder_policy=AccumulationRemainderPolicy.STEP_PARTIAL,
            worker_count=2,
            pin_memory=False,
            persistent_workers=True,
        )
        assert profile.effective_batch_size == 128

    def test_worker_count_zero_with_persistent_workers_rejected(self):
        with pytest.raises(ValidationError):
            BatchingProfile(
                identifier="test_batch",
                micro_batch_size=32,
                gradient_accumulation_steps=4,
                shuffle_policy=ShufflePolicy.EACH_EPOCH,
                incomplete_batch_policy=IncompleteBatchPolicy.KEEP,
                accumulation_remainder_policy=AccumulationRemainderPolicy.STEP_PARTIAL,
                worker_count=0,
                pin_memory=False,
                persistent_workers=True,
            )

    def test_missing_fields_rejected(self):
        with pytest.raises(ValidationError):
            BatchingProfile(
                identifier="test_batch",
                micro_batch_size=32,
                shuffle_policy=ShufflePolicy.EACH_EPOCH,
                incomplete_batch_policy=IncompleteBatchPolicy.KEEP,
                accumulation_remainder_policy=AccumulationRemainderPolicy.STEP_PARTIAL,
                worker_count=2,
                pin_memory=False,
                persistent_workers=False,
            )


# ---------------------------------------------------------------------------
# TrainingProfile discriminated union
# ---------------------------------------------------------------------------


class _BaseTraining:
    """Shared fixtures for training profile tests."""

    @pytest.fixture
    def base_kwargs(self):
        return {
            "identifier": TrainingProfileId("test_training"),
            "model_architecture_id": "test_ae",
            "optimizer_id": "test_adam",
            "batching_profile_id": "test_batch",
            "checkpoint_authorization": CheckpointAuthorization.INDEPENDENT_SELECTION,
        }

    @pytest.fixture
    def full_participation(self):
        return FullParticipationProfile(
            policy=ParticipationPolicy.FULL, minimum_available_clients=5
        )


class TestCentralizedTrainingProfile(_BaseTraining):
    def test_construction(self, base_kwargs):
        profile = CentralizedTrainingProfile(
            algorithm=TrainingAlgorithm.CENTRALIZED,
            local_epochs=10,
            **base_kwargs,
        )
        assert profile.local_epochs == 10


class TestFedAvgTrainingProfile(_BaseTraining):
    def test_positive_local_epochs(self, base_kwargs, full_participation):
        profile = FedAvgTrainingProfile(
            algorithm=TrainingAlgorithm.FEDAVG,
            local_epochs=5,
            participation=full_participation,
            **base_kwargs,
        )
        assert profile.local_epochs == 5


class TestFedProxTrainingProfile(_BaseTraining):
    def test_positive_proximal_coefficients(self, base_kwargs, full_participation):
        profile = FedProxTrainingProfile(
            algorithm=TrainingAlgorithm.FEDPROX,
            local_epochs=5,
            participation=full_participation,
            proximal_coefficients=(0.1, 0.01, 0.001),
            **base_kwargs,
        )
        assert profile.proximal_coefficients == (0.1, 0.01, 0.001)

    def test_empty_coefficients_rejected(self, base_kwargs, full_participation):
        with pytest.raises(ValidationError):
            FedProxTrainingProfile(
                algorithm=TrainingAlgorithm.FEDPROX,
                local_epochs=5,
                participation=full_participation,
                proximal_coefficients=(),
                **base_kwargs,
            )


class TestDittoTrainingProfile(_BaseTraining):
    def test_positive_personalization_weights(self, base_kwargs, full_participation):
        profile = DittoTrainingProfile(
            algorithm=TrainingAlgorithm.DITTO,
            global_local_epochs=3,
            personalized_local_epochs=5,
            participation=full_participation,
            personalization_weights=(1.0, 0.5, 0.1),
            **base_kwargs,
        )
        assert profile.personalization_weights == (1.0, 0.5, 0.1)

    def test_empty_weights_rejected(self, base_kwargs, full_participation):
        with pytest.raises(ValidationError):
            DittoTrainingProfile(
                algorithm=TrainingAlgorithm.DITTO,
                global_local_epochs=3,
                personalized_local_epochs=5,
                participation=full_participation,
                personalization_weights=(),
                **base_kwargs,
            )


class TestTrainingProfileInvalid:
    def test_wrong_algorithm_rejected(self):
        with pytest.raises(ValidationError):
            CentralizedTrainingProfile(
                identifier=TrainingProfileId("bad"),
                model_architecture_id="ae",
                optimizer_id="adam",
                batching_profile_id="batch",
                checkpoint_authorization=CheckpointAuthorization.INDEPENDENT_SELECTION,
                algorithm=TrainingAlgorithm.FEDAVG,
                local_epochs=10,
            )

    def test_unknown_fields_rejected(self):
        with pytest.raises(ValidationError):
            CentralizedTrainingProfile(
                identifier=TrainingProfileId("bad"),
                model_architecture_id="ae",
                optimizer_id="adam",
                batching_profile_id="batch",
                checkpoint_authorization=CheckpointAuthorization.INDEPENDENT_SELECTION,
                algorithm=TrainingAlgorithm.CENTRALIZED,
                local_epochs=10,
                unknown_field="xyz",
            )


# ---------------------------------------------------------------------------
# SeedCohortProfile
# ---------------------------------------------------------------------------


class TestSeedCohortProfile:
    def test_training_seeds_count_equals_paired_seed_count(self):
        profile = SeedCohortProfile(
            identifier=SeedCohortId("test_cohort"),
            paired_seed_count=3,
            training_seeds=(Seed(1), Seed(2), Seed(3)),
            bootstrap_analysis_seed=Seed(42),
            analysis_seed_model=SeedAnalysisModel.PAIRED,
        )
        assert len(profile.training_seeds) == 3

    def test_count_mismatch_rejected(self):
        with pytest.raises(ValidationError):
            SeedCohortProfile(
                identifier=SeedCohortId("test_cohort"),
                paired_seed_count=2,
                training_seeds=(Seed(1), Seed(2), Seed(3)),
                bootstrap_analysis_seed=Seed(42),
                analysis_seed_model=SeedAnalysisModel.PAIRED,
            )

    def test_duplicate_seeds_rejected(self):
        with pytest.raises(ValidationError):
            SeedCohortProfile(
                identifier=SeedCohortId("test_cohort"),
                paired_seed_count=3,
                training_seeds=(Seed(1), Seed(2), Seed(1)),
                bootstrap_analysis_seed=Seed(42),
                analysis_seed_model=SeedAnalysisModel.PAIRED,
            )

    def test_unique_seeds_accepted(self):
        profile = SeedCohortProfile(
            identifier=SeedCohortId("test_cohort"),
            paired_seed_count=5,
            training_seeds=(Seed(10), Seed(20), Seed(30), Seed(40), Seed(50)),
            bootstrap_analysis_seed=Seed(99),
            analysis_seed_model=SeedAnalysisModel.PAIRED,
        )
        assert len(set(profile.training_seeds)) == 5


# ---------------------------------------------------------------------------
# CheckpointProfile
# ---------------------------------------------------------------------------


class TestCheckpointProfile:
    def test_sorted_capture_rounds_accepted(self):
        selection = FixedRoundSelection(
            kind=CheckpointSelectionKind.FIXED_ROUND, selected_round=30
        )
        profile = CheckpointProfile(
            identifier=CheckpointProfileId("test_cp"),
            total_rounds=100,
            capture_rounds=(10, 20, 30),
            save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
            selection=selection,
        )
        assert profile.capture_rounds == (10, 20, 30)

    def test_unsorted_capture_rounds_rejected(self):
        selection = FixedRoundSelection(
            kind=CheckpointSelectionKind.FIXED_ROUND, selected_round=50
        )
        with pytest.raises(ValidationError):
            CheckpointProfile(
                identifier=CheckpointProfileId("test_cp"),
                total_rounds=100,
                capture_rounds=(50, 10, 30),
                save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
                selection=selection,
            )

    def test_capture_round_beyond_total_rejected(self):
        selection = FixedRoundSelection(
            kind=CheckpointSelectionKind.FIXED_ROUND, selected_round=50
        )
        with pytest.raises(ValidationError):
            CheckpointProfile(
                identifier=CheckpointProfileId("test_cp"),
                total_rounds=100,
                capture_rounds=(10, 50, 150),
                save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
                selection=selection,
            )

    def test_fixed_round_missing_from_capture_rejected(self):
        with pytest.raises(ValidationError):
            CheckpointProfile(
                identifier=CheckpointProfileId("test_cp"),
                total_rounds=100,
                capture_rounds=(10, 20, 30),
                save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
                selection=FixedRoundSelection(
                    kind=CheckpointSelectionKind.FIXED_ROUND, selected_round=50
                ),
            )

    def test_convergence_requires_final_round_captured(self):
        selection = FirstQualifyingConvergenceSelection(
            kind=CheckpointSelectionKind.FIRST_QUALIFYING_CONVERGENCE,
            initial_rounds=20,
            window_rounds=10,
            relative_loss_tolerance=0.05,
            tie_break=CheckpointTieBreak.EARLIEST_ROUND,
            no_qualifying_round=NoQualifyingRoundPolicy.FINAL_ROUND,
        )
        with pytest.raises(ValidationError):
            CheckpointProfile(
                identifier=CheckpointProfileId("test_cp"),
                total_rounds=100,
                capture_rounds=(10, 20, 30, 40),
                save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
                selection=selection,
            )

    def test_convergence_with_final_round_accepted(self):
        selection = FirstQualifyingConvergenceSelection(
            kind=CheckpointSelectionKind.FIRST_QUALIFYING_CONVERGENCE,
            initial_rounds=20,
            window_rounds=10,
            relative_loss_tolerance=0.05,
            tie_break=CheckpointTieBreak.EARLIEST_ROUND,
            no_qualifying_round=NoQualifyingRoundPolicy.FINAL_ROUND,
        )
        profile = CheckpointProfile(
            identifier=CheckpointProfileId("test_cp"),
            total_rounds=50,
            capture_rounds=(10, 20, 30, 40, 50),
            save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
            selection=selection,
        )
        assert profile.total_rounds == 50

    def test_lowest_loss_selection_accepted(self):
        selection = LowestCalibrationLossSelection(
            kind=CheckpointSelectionKind.LOWEST_CALIBRATION_LOSS,
            tie_break=CheckpointTieBreak.LATEST_ROUND,
        )
        profile = CheckpointProfile(
            identifier=CheckpointProfileId("test_cp"),
            total_rounds=50,
            capture_rounds=(10, 20, 30, 40, 50),
            save_policy=CheckpointSavePolicy.CONFIGURED_ROUNDS,
            selection=selection,
        )
        assert profile.total_rounds == 50


# ---------------------------------------------------------------------------
# SplitProfile discriminated union
# ---------------------------------------------------------------------------


class TestStandardSplitProfile:
    def test_correct_split_memberships(self):
        profile = StandardSplitProfile(
            kind=SplitProfileKind.STANDARD,
            training=SplitMembership.TRAIN,
            calibration=SplitMembership.CALIBRATION,
            test=SplitMembership.TEST,
        )
        assert profile.training == SplitMembership.TRAIN
        assert profile.calibration == SplitMembership.CALIBRATION
        assert profile.test == SplitMembership.TEST

    def test_invalid_membership_rejected(self):
        with pytest.raises(ValidationError):
            StandardSplitProfile(
                kind=SplitProfileKind.STANDARD,
                training=SplitMembership.TRAIN,
                calibration=SplitMembership.CALIBRATION,
                test=SplitMembership.HISTORICAL_TRAINING,
            )


class TestTemporalSplitProfile:
    def test_correct_split_memberships(self):
        profile = TemporalSplitProfile(
            kind=SplitProfileKind.TEMPORAL,
            training=SplitMembership.HISTORICAL_TRAINING,
            calibration=SplitMembership.HISTORICAL_CALIBRATION,
            future_recalibration=SplitMembership.FUTURE_RECALIBRATION,
            test=SplitMembership.FUTURE_EVALUATION,
        )
        assert profile.training == SplitMembership.HISTORICAL_TRAINING
        assert profile.future_recalibration == SplitMembership.FUTURE_RECALIBRATION
        assert profile.test == SplitMembership.FUTURE_EVALUATION

    def test_invalid_membership_rejected(self):
        with pytest.raises(ValidationError):
            TemporalSplitProfile(
                kind=SplitProfileKind.TEMPORAL,
                training=SplitMembership.HISTORICAL_TRAINING,
                calibration=SplitMembership.HISTORICAL_CALIBRATION,
                future_recalibration=SplitMembership.FUTURE_RECALIBRATION,
                test=SplitMembership.TEST,
            )


# ---------------------------------------------------------------------------
# LearningDataSchema
# ---------------------------------------------------------------------------


class TestLearningDataSchema:
    def test_valid_with_standard_split(self):
        split = StandardSplitProfile(
            kind=SplitProfileKind.STANDARD,
            training=SplitMembership.TRAIN,
            calibration=SplitMembership.CALIBRATION,
            test=SplitMembership.TEST,
        )
        schema = LearningDataSchema(
            identifier="test_schema",
            feature_columns=("feature_a", "feature_b", "feature_c"),
            split_profile=split,
        )
        assert len(schema.feature_columns) == 3

    def test_valid_with_temporal_split(self):
        split = TemporalSplitProfile(
            kind=SplitProfileKind.TEMPORAL,
            training=SplitMembership.HISTORICAL_TRAINING,
            calibration=SplitMembership.HISTORICAL_CALIBRATION,
            future_recalibration=SplitMembership.FUTURE_RECALIBRATION,
            test=SplitMembership.FUTURE_EVALUATION,
        )
        schema = LearningDataSchema(
            identifier="test_schema",
            feature_columns=("feature_x", "feature_y"),
            split_profile=split,
        )
        assert len(schema.feature_columns) == 2

    def test_empty_feature_columns_rejected(self):
        split = StandardSplitProfile(
            kind=SplitProfileKind.STANDARD,
            training=SplitMembership.TRAIN,
            calibration=SplitMembership.CALIBRATION,
            test=SplitMembership.TEST,
        )
        with pytest.raises(ValidationError):
            LearningDataSchema(
                identifier="test_schema",
                feature_columns=(),
                split_profile=split,
            )

    def test_duplicate_feature_columns_rejected(self):
        split = StandardSplitProfile(
            kind=SplitProfileKind.STANDARD,
            training=SplitMembership.TRAIN,
            calibration=SplitMembership.CALIBRATION,
            test=SplitMembership.TEST,
        )
        with pytest.raises(ValidationError):
            LearningDataSchema(
                identifier="test_schema",
                feature_columns=("f1", "f2", "f1"),
                split_profile=split,
            )
