# Phase 08 — Federated Training, Checkpointing, and Scoring

## Scientific authority

`docs/Journal_Extension_Master_Roadmap.md` remains authoritative for the scientific question, evidence tiers, datasets, training protocol, checkpoint candidates, fixed-detector comparison, and permitted claims. The cross-cutting ownership rules in `18_REPOSITORY_ARCHITECTURE_AND_SCIENTIFIC_INVARIANTS.md` govern the internal package layout without changing those scientific contracts.

## Objective

Implement and verify:

- the FedAvg confirmatory detector;
- the FedProx training stress-test grid;
- genuine Ditto global and persistent client-personalized models;
- fixed-terminal, non-test checkpoint selection;
- immutable calibration and evaluation score artifacts reusable across threshold methods;
- typed publication and trusted reuse for every model family.

## Fixed scientific contract

Within one seed, population, preprocessing protocol, split protocol, and model coordinate:

- training occurs once;
- one selected detector is frozen;
- calibration and evaluation scores are generated once;
- threshold methods receive identical model, preprocessing, split, client, score, label, and row evidence;
- threshold identity never enters training, checkpoint, or scoring coordinates;
- attack labels and held-out metrics never enter checkpoint selection;
- AUROC is a fixed-score control rather than a threshold verdict.

## Preprocessing ownership

Confirmatory federated training consumes `FEDERATED_CLIENT_LOCAL_STANDARD`: one client-local `StandardScaler` fitted only on that client’s benign training partition. Supportive pooled-MinMax execution uses `FEDERATED_POOLED_MIN_MAX` under a distinct protocol identity. Training must not fit, replace, or infer preprocessing.

## Model requirements

### Shared autoencoder

- Architecture is protocol-driven and the dataset input width is explicit.
- Initialization is deterministic from the declared training seed.
- Forward output shape equals input shape.
- No BatchNorm or threshold-specific behavior is introduced.
- Reconstruction-error semantics have one scoring implementation.

### FedAvg

- one local epoch per round;
- full client participation;
- sample-count-weighted aggregation;
- declared optimizer, batch size, learning rate, and round budget only;
- one global model state per coordinate;
- round-level client participation, loss, state checksum, and communication evidence are persisted.

### FedProx

- the proximal term is computed against the current global state;
- every declared positive coefficient is an independent training coordinate;
- the stress-test grid is reportable without promoting a primary coefficient;
- FedProx results never enter the FedAvg confirmatory ladder.

The primary FedProx coefficient-selection rule remains scientifically unresolved. The implementation must retain the complete declared grid and return typed unresolved selection rather than inventing a primary coefficient.

### Ditto

- one global state and one persistent personalized state per client;
- personalized states persist across rounds;
- the personalized proximal objective is computed toward the current global state;
- personalized states are never aggregated as global updates;
- global and personalized checkpoints and scores use distinct coordinates;
- the global and personalized artifact trees are one related publication and must commit or roll back together.

## Checkpoint bounded context

The checkpoint implementation is owned by `datp_core.learning.federated.checkpoints`:

- `identities.py` — asset and manifest identities;
- `documents.py` — strict persisted checkpoint documents;
- `history.py` — training-history persistence and validation;
- `candidates.py` — tensor names, candidate retention, validation, and rebasing;
- `selection.py` — fixed-terminal selection and leakage rejection;
- `publication.py` — checkpoint and history writing;
- `reuse.py` — trusted loading and provenance validation.

The former `learning/federated/checkpointing.py` module is deleted. It must not be restored, aliased, or re-exported.

## Checkpoint protocol

- Candidate rounds are exactly `{25, 50, 75, 100, 125, 150, 200}`.
- The primary journal checkpoint is always `CheckpointProtocol.maximum_round` (`200`) under `FIXED_TERMINAL_MAXIMUM_ROUND`.
- Non-terminal candidates are stability evidence only.
- Training loss may be recorded but cannot select the primary checkpoint.
- Held-out AUROC, FPR, CV(FPR), Macro-F1, balanced accuracy, attack labels, threshold effects, external outcomes, and policy-specific outcomes are rejected as selection inputs.
- Centralized and federated candidate inventories remain independent.
- Historical anchor endpoints remain isolated from the journal rule.

## Scoring and reuse

A federated score coordinate includes population, seed, model identity, model coefficient when applicable, preprocessing identity, split identity, and selected checkpoint. It excludes threshold method, quantile, calibration-size ablation, and analysis method.

A completed score inventory is reusable only when all of the following match:

- selected checkpoint checksum and round;
- preprocessing-state-set checksum;
- split-manifest checksum;
- client inventory;
- scored partition inventory;
- feature schema and count;
- source rows and labels;
- persisted Parquet checksums.

The scoring service writes into a caller-owned empty directory. The orchestration artifact codec is the sole owner of atomic staging, replacement, reuse loading, and path rebasing. Nested atomic publication is forbidden.

## Publication architecture

Federated training and scoring use the neutral lifecycle in `pipeline/publication`:

1. write a typed complete artifact into staging;
2. validate scientific compatibility and file integrity;
3. load a trusted persisted result for reuse;
4. rebase paths after atomic publication.

Ditto uses related-directory publication so its global and personalized trees are validated and committed as one unit with rollback.

## Required scientific tests

- Every threshold method for one frozen FedAvg cell sees identical model, calibration-score, evaluation-score, preprocessing, and split checksums.
- Score files and source-row order remain byte-identical after all threshold constructions.
- AUROC over unchanged scores is invariant across threshold methods.
- Training, checkpoint, and score dataclasses expose no threshold-policy field.
- Held-out metrics and attack-label presence are rejected by checkpoint selection.
- Only the maximum-round candidate receives selected status.
- Ditto personalized states differ across clients and persist across rounds.
- Ditto global and personalized directories cannot be partially published or reused.
- FedProx zero is not exposed as a stress-test coefficient.
- Batch size is never reduced silently.

## Implementation record

Implemented source ownership includes:

- `learning/autoencoder.py`;
- `learning/federated/models.py` and `training.py`;
- `learning/federated/{fedavg,fedprox,ditto}.py`;
- `learning/federated/checkpoints/` split bounded context;
- `pipeline/checkpoints/`, `pipeline/scoring/`, and `pipeline/publication/`;
- `scoring/{models,generation}.py`;
- orchestration stages for federated training, checkpoint selection, and scoring.

The refactor removed:

- the checkpoint god module;
- compatibility imports from that path;
- nested score publication;
- artifact-store re-exports of neutral publication helpers;
- duplicate checkpoint-file validation;
- direct canonical serialization outside the artifact boundary.

## Unchanged scientific blockers

- FedProx primary-coefficient promotion remains unresolved; the complete grid remains executable and reportable.
- No threshold algorithm, metric, cohort, dataset rule, seed cohort, or evidence tier is changed by the architecture refactor.

## Status

The Phase 08 scientific implementation remains complete. The repository-architecture refactor is **implemented but requires final-head validation** before merge acceptance.

Do not claim the refactor is fully audited until the current PR head passes:

- Ruff format and lint;
- Pyright;
- Pylint;
- import-linter;
- architecture tests;
- Phase 08 unit tests;
- FedAvg, FedProx, and Ditto integration tests;
- fixed-detector and checkpoint-leakage scientific tests;
- the complete pytest suite.

At the time of this update, no GitHub Actions run had been observed for the then-current PR head. This is an explicit validation status, not a scientific blocker.

## Exit criteria

- FedAvg, FedProx, and genuine Ditto produce independent safe model artifacts.
- Ditto related artifacts cannot be partially committed or reused.
- Checkpoint selection is fixed-terminal, non-test, and model-specific.
- Scores are immutable and reusable across threshold methods.
- Fixed-detector invariants are machine-verifiable.
- The checkpoint monolith and all legacy imports remain absent.
- The final PR head passes the focused and complete verification gates.
