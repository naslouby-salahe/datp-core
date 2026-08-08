# Training, checkpoint, and scoring review

Scope: read-only Graphify-assisted review of detector training, checkpoint retention/selection, score generation, centralized reference, FedProx, Ditto, and their execution callers. The full roadmap had been read before the review; `00_JOURNAL_CONTRACT.md` was reread before classification.

## Verified live workflow graph

- Production standard route: `datp_core.app.cli.app:main` → recipe/declared execution → `PipelineStageRunner` → `ExperimentWorkspace.training` → `train_federated_detector` → `run_federated_training` → persisted candidates → `ExperimentWorkspace.selection` → `score_selected_checkpoint` → `publish_federated_scores` → frozen-score evaluation.
- Graphify queries linked `selection.py`, `score_generation.py`, `score_selected_checkpoint`, the workspace, federated scoring, centralized scoring, training stress, and experiment runners. Every material path below was verified in source because Graphify traversal includes inferred/type-reference edges.
- Standard FedAvg/FedProx uses `CHECKPOINT_PROTOCOL=(25,50,75,100,125,150,200)` and `FIXED_TERMINAL_MAXIMUM_ROUND`. `select_checkpoint` rejects held-out metrics/attack labels, validates checkpoint preprocessing/split provenance, and selects the terminal candidate.
- `run_federated_training` uses each declared client per round, one local epoch per `FedAvgProtocol`/`FedProxProtocol`, trains only benign-labelled rows, records sample-weighted FedAvg aggregation, and retains only declared snapshots. FedProx adds the proximal term against the current global state and is routed under a distinct model/coefficient coordinate.
- Ditto trains a separate global update and a persistent client-specific personalized update each round, aggregates only global updates, persists personalized candidates per client, and scores each personalized checkpoint separately. The stress runner then applies B1/B2 to the same collected personalized score artifacts.
- B0 has a separate centralized population-preprocessing, training coordinate/model identity, candidate set, selected terminal checkpoint, pooled score artifacts, and pooled quantile; it does not reuse FedAvg tensors or scores.

## Confirmed issue

### TS-001

- **Severity:** HIGH
- **Disposition:** FIX_RUNTIME_BUG
- **File:** `src/datp_core/detector/training/centralized_publication.py:165-184`; consequentially `src/datp_core/detector/scoring/centralized.py:83-108`
- **Symbol:** `centralized_training_is_reusable`; `load_reused_centralized_training`; `centralized_scoring_is_reusable`
- **Roadmap requirement:** B0 must be an independently trained centralized reference using its own pooled-min-max preprocessing fitted on current pooled benign training records; preprocessing is part of detector state and persisted/reused artifacts must retain exact provenance (roadmap §§2.2.1, 4.1; catalogue §§3.1, 5.1).
- **Roadmap section:** §§2.2.1 and 4.1; catalogue §3.1.
- **Graphify evidence:** Graphify traversal connects `experiments/centralized_reference.py` to `train_centralized_detector`, centralized candidate selection, and `generate_centralized_scores`; the centralized publication codec's reuse validator is therefore on the production B0 root, not merely an unused helper.
- **Direct source evidence:**
  - `centralized_training_is_reusable` accepts an existing directory when only `COMPLETE`, model tensor, history, and candidate filenames exist, and the completion digest equals `checksum(model_tensor | maximum_round | batch_size)`. It does not validate the requested coordinate, seed, autoencoder widths, feature schema, preprocessing checksum, split checksum, candidate checksums, or training input identity.
  - `load_reused_centralized_training` then reconstructs `CentralizedTrainingResult.preprocessing_state_checksum`, `split_manifest_checksum`, coordinate, seed, and architecture from the *current request* while pointing at the existing tensor files. This rebrands stale tensors as if they came from the current preprocessing/split.
  - Centralized score reuse checks only score-file completion plus row-id/label binding (`_score_partition_binding`); it does not bind source transformed feature values. Because the reloaded training result has been rebranded, a stale checkpoint and stale scores can pass after a preprocessing/split/content change that preserves row identities and labels.
  - By contrast, federated reuse loads and validates a candidate manifest containing coordinate, preprocessing-state-set checksum, split checksum, widths, batch size, candidate rounds, and tensor checksums (`detector/checkpoints/reuse.py`, `detector/checkpoints/publication.py`).
- **Current callers:** `experiments/centralized_reference.py:run_centralized_reference_seed` → `train_centralized_detector`; standard artifact publication invokes the reusable validator before loader reuse.
- **Current callees:** stale `CentralizedTrainingResult` feeds centralized terminal selection, `generate_centralized_scores`, pooled threshold construction, and B0 evaluation.
- **Production reachable:** YES.
- **Test-only reachable:** NO.
- **Scientifically required:** YES (B0 is contextual but mandatory independent reference logic).
- **Problem:** the B0 cache's identity is materially under-specified. A complete marker alone permits reusing artifacts trained from a different current preprocessing/split/input state, while the loader asserts current provenance values without demonstrating them.
- **Scientific consequence:** B0 can cease to be an independently trained centralized reference for the current frozen preprocessing/data state. The implementation may report a pooled threshold/evaluation as current B0 while model scores derive from an older population transformation. This violates the fixed detector/provenance contract and can invalidate contextual comparisons.
- **Runtime consequence:** silent stale-artifact reuse rather than a rerun or integrity error.
- **Architecture consequence:** centralized artifact reuse is inconsistent with the stronger manifest-bound federated artifact design.
- **Correct final state:** add a persisted centralized training manifest/complete digest that binds at least coordinate, training seed, model/architecture, checkpoint protocol/candidate tensor checksums, preprocessing checksum, split checksum, feature schema/checksum, declared optimizer values, and an input-frame checksum. Validate it before reuse; do not reconstruct provenance from the request until the persisted identity matches. Bind centralized score reuse to selected checkpoint checksum, preprocessing checksum, split checksum, feature names, and a checksum of transformed calibration/evaluation inputs (row identity plus feature values), or force regeneration when any differs.
- **Affected callers:** `run_centralized_reference_seed`; all centralized reference pipeline/reuse paths.
- **Affected callees:** centralized checkpoint selection, centralized scoring, pooled threshold/evaluation, B0 publication.
- **Affected tests:** extend `tests/integration/pipeline/test_centralized_reference.py`, `tests/unit/pipeline/checkpoints/test_centralized_checkpoints.py`, `tests/unit/pipeline/scoring/test_centralized_scoring.py`, and reuse-specific tests with changed preprocessing/split/feature values retaining identical row IDs.
- **Affected artifacts:** B0 `training/COMPLETE`, centralized training history/candidates/model tensor, `scores/COMPLETE`, centralized score parquet files.
- **Confidence:** CONFIRMED.

## Verified intentional implementations (not issues)

- **FedAvg/FedProx checkpoint discipline:** `run_federated_training` captures exact declared rounds. `select_federated_primary_checkpoint` validates candidate provenance, rejects held-out inputs and attack labels, and selects 200 only. FedProx candidates are separately coordinated by coefficient.
- **FedProx selection is outcome-blind:** `collect_fedprox_coefficient_terminal_losses` reads only persisted round-200 aggregate training loss across the locked confirmatory seed cohort; `select_primary_fedprox_coefficient` requires the exact frozen grid and uses minimum loss with smallest-coefficient tiebreak. The primary coefficient is not chosen from FPR, threshold, attack, or external results.
- **Ditto semantics:** personalized states initialize separately per client, update against the global-state proximal reference, remain persistent across rounds, are never passed to `aggregate_client_updates`, and are retained/scored per client. The global state alone is aggregated. This satisfies the roadmap's genuine-Ditto naming constraint.
- **Fixed-score guards:** federated scoring accepts only `SELECTED_BY_NON_TEST_RULE` checkpoints; score manifests record selected model checksum, calibration/evaluation score-set checksums, preprocessing checksum, and split checksum. Scoring excludes training and static-reference-reserve partitions. `ExperimentWorkspace.comparison_fixed_score_evidence` validates cross-policy score provenance and AUROC invariance when comparison artifacts are available.
- **Centralized separation in live execution:** B0 builds a `CentralizedTrainingCoordinate`, uses `CENTRALIZED_POOLED_MIN_MAX`, invokes centralized training/scoring APIs, and obtains its own terminal candidate. The defect above is cache identity, not a FedAvg-to-B0 relabelling path.

## Coverage and conclusion

Reviewed production training, persistence/reuse, candidate retention/selection, federated/centralized scoring, fixed-score provenance, standard workspace orchestration, B0 execution, and the FedProx/Ditto stress runners. Found **one confirmed high-severity reachable runtime/provenance defect** in centralized cache reuse. No suspected-only findings are retained in this review. FedAvg, FedProx, Ditto, terminal checkpoint, benign-only training, and federated fixed-score semantics are otherwise implemented and wired in the inspected paths.
