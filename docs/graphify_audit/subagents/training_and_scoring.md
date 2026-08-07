# Audit: Training, Checkpointing, and Scoring

Scope: `src/datp_core/learning/`, `src/datp_core/pipeline/decision/`,
`src/datp_core/pipeline/scoring/`, `src/datp_core/pipeline/training/`,
`src/datp_core/pipeline/workflows/personalization*.py`,
`src/datp_core/pipeline/execution/`, `src/datp_core/protocols/{training,checkpoints,inference}.py`,
`src/datp_core/evaluation/fixed_score/`.
Roadmap sections checked: 2.3, 2.4, 2.5, 7.1, 7.2, 3.10, 3.11, 11.1, 11.2, 13.1.

## Verdict summary

| Question | Verdict |
|---|---|
| FedAvg training correct | PASS |
| FedProx separate from FedAvg | PASS |
| Ditto genuine semantics | PASS |
| FIXED_TERMINAL_MAXIMUM_ROUND=200 applied | PASS |
| Checkpoints {25,50,75,100,125,150,200} saved/selectable | PASS (all saved; only 200 selectable by design) |
| Same scores reused across B1-B4 | PASS |
| Reconstruction error = MSE, higher = more anomalous | PASS |
| Centralized / federated separation | PASS |

## 1. FedAvg training

Correct full-participation FedAvg.

- `src/datp_core/learning/federated/training.py:519-638` `run_federated_training`: every round, every client runs one local epoch from the current global state; updates aggregated sample-count-weighted.
- `src/datp_core/learning/federated/training.py:358-398` `aggregate_client_updates`: weighted mean over sample counts, computed in float64 then cast back to float32.
- `src/datp_core/learning/federated/training.py:401-413` `compute_weighted_aggregate_loss`: population-weighted aggregate training loss.
- `src/datp_core/learning/federated/training.py:544-548`: deterministic init via `build_reconstruction_autoencoder(initialization_seed=training_seed)`.
- `src/datp_core/learning/federated/training.py:531`: clients sorted for deterministic order; per-round/client shuffle seed derived at `training.py:185-193`.
- `src/datp_core/learning/federated/training.py:504-516` `_proximal_coefficient`: FedAvg => `None` (no proximal term).
- Protocol carries no coefficient: `src/datp_core/protocols/training.py:78-82`; coordinate rejects a coefficient: `src/datp_core/learning/federated/models/coordinates.py:21-24`; `src/datp_core/learning/federated/global_training.py:35-40` forbids a coefficient on FedAvg coordinates.

## 2. FedProx separate from FedAvg

PASS. Distinct protocol, frozen grid, separate dispatch, genuine proximal objective.

- `src/datp_core/protocols/training.py:84-89` `FedProxProtocol` (distinct StrictModel with `coefficient`); `training.py:162` frozen grid `FEDPROX_COEFFICIENTS=(0.001,0.01,0.1,1.0)`.
- `src/datp_core/protocols/training.py:293-318` `resolve_single_model_federated_training_protocol`: dispatches by `TrainingModelId`; FedProx resolves its declared coefficient.
- `src/datp_core/learning/federated/training.py:566-568`: `ProximalTerm(global_state, proximal_coefficient)` applied only when coefficient is not None.
- `src/datp_core/learning/federated/training.py:214-228` `proximal_penalty`: `mu/2 * sum(||w - w_t||^2)` over all parameters (standard FedProx).
- `src/datp_core/learning/federated/global_training.py:41-46` `_validate_protocol_binding`: FedProx coordinate coefficient must equal protocol coefficient.
- Coefficient selection uses non-test rule `FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS` at round 200, benign training loss only: `src/datp_core/protocols/training.py:163-217`, `src/datp_core/pipeline/workflows/personalization.py:569-664`.

## 3. Ditto genuine semantics

PASS. Matches Ditto (Li et al. ICML 2021) and roadmap 7.2 / 3.11 / 11.2.

- `src/datp_core/learning/federated/ditto.py:104-266` `train_ditto`:
  - Distinct global model: `global_state` (line 127).
  - Persistent per-client personalized states: `personalized_states` (line 129), carried across rounds.
  - Per round, per client: global contribution = `train_client_update(initial_state=global_state)` with NO proximal term (lines 145-159) — the FedAvg-style global update.
  - Personalized model = `train_client_update(initial_state=p_state, proximal_term=ProximalTerm(reference_state=global_state, coefficient=regularization))` (lines 161-179) — personalized objective `L_k(v) + lambda/2 ||v - w_t||^2`.
  - Only global updates aggregated (`aggregate_client_updates`, line 211); personalized states never aggregated into the global model.
  - Personalized state checksums published per client per round (lines 190-200); personalized snapshots saved per client at candidate rounds (lines 202-209).
- Separate global/personalized publication dirs and per-client candidate files `checkpoint_round_<r>_client_<id>.safetensors`: `src/datp_core/learning/federated/checkpoints/candidates.py:35-43`, `publication.py:357-418`.
- Coordinate pairing enforced: `src/datp_core/learning/federated/models/coordinates.py:80-97` `matches_ditto_peer`, `DittoTrainingCoordinates` (100-148).
- Roadmap-required Ditto semantics all present: distinct global model; persistent client-personalized states; correct proximal personalized objective; no aggregation of personalized states as global; separate evaluation (Ditto scores generated from per-client personalized checkpoints at `personalization.py:896-962`).

## 4. Checkpoint selection rule (FIXED_TERMINAL_MAXIMUM_ROUND = 200)

PASS.

- `src/datp_core/protocols/training.py:119-123`: `CHECKPOINT_PROTOCOL = CheckpointProtocol(candidates=(25,50,75,100,125,150,200), maximum_round=200)`; `CHECKPOINT_SELECTION_RULE = FIXED_TERMINAL_MAXIMUM_ROUND`.
- `src/datp_core/protocols/checkpoints.py:16-27`: protocol requires final candidate == maximum_round; candidates unique/ordered.
- `src/datp_core/protocols/checkpoints.py:98-126` `select_terminal_checkpoint`: max-round candidate gets `SELECTED_BY_NON_TEST_RULE`; all others `STABILITY_EVIDENCE`.
- `src/datp_core/protocols/training.py:126-148` `require_non_test_checkpoint_selection_inputs`: rejects held-out metrics, attack labels, any other selection rule.
- Enforced downstream: federated `src/datp_core/learning/federated/checkpoints/selection.py:66-107` and `models/checkpoints.py:83-87` (decision requires `selected.round_number == maximum_round`); centralized `src/datp_core/pipeline/checkpoints/service.py:142-176` and `models.py:97-101`.
- Roadmap 2.5 / 13.1 (lines 1269-1288, 3467) match: 200 max round, non-test rule, non-terminal retained as stability evidence only.

## 5. Checkpoint candidates all saved

PASS — all 7 saved and integrity-verified; only round 200 is selectable (per design, others are stability evidence).

- Federated: snapshots captured at candidate rounds `src/datp_core/learning/federated/training.py:611-618`; persisted via `retain_checkpoint_candidates` `src/datp_core/learning/federated/checkpoints/candidates.py:90-123` which requires observed rounds == protocol candidates exactly; atomic safetensors write with reload-equality assert (`candidates.py:46-87`).
- Ditto: global + per-client personalized snapshots at candidate rounds (`ditto.py:202-209`, `237-238`).
- Centralized: snapshots at candidate rounds `src/datp_core/learning/centralized/training.py:503-510`; persisted `src/datp_core/pipeline/checkpoints/service.py:106-140`.
- Execution invariants require exact candidate set: `src/datp_core/learning/federated/models/checkpoints.py:174-181`, `src/datp_core/learning/centralized/training.py:161-167`.
- Reuse reload re-validates every candidate file + checksum: `src/datp_core/learning/federated/checkpoints/reuse.py:107-158`, `src/datp_core/pipeline/training/centralized.py:274-303`.

## 6. Same scores reused across B1-B4

PASS.

- Score artifacts live under `federated_training_directory(...) / SCORES`: `src/datp_core/pipeline/execution/workspace.py:136-146`, layout keyed by `FederatedTrainingCoordinate` (`src/datp_core/pipeline/execution/layout.py:32-54`) which EXCLUDES `threshold_method`. B1/B2/B3/B4 are separate `ExperimentCoordinate`s (`src/datp_core/pipeline/coordinates.py:55-131`) sharing one training coordinate, so they share one score set.
- Score generation once per selected checkpoint; reuse guarded by `FixedScoreInvariant` checksum and `federated_scoring_is_reusable` / `load_reused_federated_scores`: `src/datp_core/pipeline/scoring/federated.py:85-145`, `src/datp_core/protocols/inference.py:152-179`.
- Cross-policy invariance enforced by `validate_fixed_score_controls` (`src/datp_core/evaluation/fixed_score/validation.py:34-120`): model checksum, selected-checkpoint checksum, preprocessing, calibration-score set, evaluation-score set, labels, source rows, score order, client population, eligibility cohort, and per-client AUROC must all match across compared threshold methods; only `threshold_method` differs.
- Workspace pulls prior method evidence and validates: `src/datp_core/pipeline/execution/workspace.py:201-223`.
- Roadmap 2.3/2.4 (lines 128-158) forbid per-policy retraining and per-policy checkpoint selection.

## 7. Reconstruction error (MSE, higher = more anomalous)

PASS.

- `src/datp_core/learning/autoencoder.py:166-202` `reconstruction_errors`: per-row `mean((reconstruction - batch)^2, dim=1)` in float32 on CUDA, `torch.inference_mode()`, model in eval mode.
- Score frame schema stores value as `RECONSTRUCTION_ERROR` (Float64): `src/datp_core/pipeline/scoring/frames.py:31-42`, `73-93`.
- Input validation (2-D, width match, finite): `autoencoder.py:129-144`.
- Matches roadmap structural definition (line 2894): MSE non-negative, higher MSE = stronger anomaly evidence; the perturbation-based polarity experiment was removed as redundant.

## 8. Centralized / federated separation

PASS.

- Distinct modules: `src/datp_core/learning/centralized/training.py` vs `src/datp_core/learning/federated/*`.
- Distinct coordinates: `CentralizedTrainingCoordinate` vs `FederatedTrainingCoordinate`.
- Cross-branch guards: `reject_federated_preprocessing_for_training` (`centralized/training.py:187-192`), `reject_centralized_checkpoint` (`federated/checkpoints/selection.py:110-116`), `reject_federated_checkpoint` (`pipeline/checkpoints/service.py:179-183`).
- Distinct scoring loaders: centralized `load_centralized_model_tensors` (`pipeline/scoring/centralized.py:78`) vs federated `load_checkpoint_model` (`pipeline/scoring/frames.py:181-196`).
- Distinct evaluation: centralized = pooled benign quantile + SUPPORTIVE evidence (`pipeline/decision/centralized.py:444`); federated = threshold ladder with fixed-score controls.
- Centralized reference workflow runs under its own `centralized_reference/` tree and never consumes federated checkpoints: `src/datp_core/pipeline/workflows/centralized.py:45-136`.

## Observations (non-blocking)

- Model init approach differs between branches: centralized uses `construct_autoencoder` under global seed set by `configure_deterministic_execution` (`centralized/training.py:210,225`); federated/Ditto use `build_reconstruction_autoencoder` with an explicit per-seed generator (`federated/training.py:544-548`, `ditto.py:123-127`). Both deterministic; approach inconsistency only.
- Centralized loader uses `drop_last=True` and requires at least one full batch (`centralized/training.py:219-223,456`); federated client loader uses `drop_last=False` (`federated/training.py:204-211`). Internally consistent, differs by design.
- Ditto global training history records aggregate loss from the unregularized global updates only; personalized losses are recorded in the separate personalized history (`ditto.py:211-233`, `checkpoints/history.py:199-220`). Intentional.

No blocking defects found.
