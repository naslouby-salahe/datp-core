# Dataset & Artifact Contracts

> Ticket: P0-T05. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §7, §17; existing `data/raw` symlink. Defines what must be true of a dataset
> before it enters the pipeline, and what every produced artifact must carry
> so that reuse is valid only when dataset/split/checkpoint/preprocessing/
> seed/scoring identity match exactly.

## 1. Dataset Contracts

Each dataset contract below is the complete set of facts a loader must verify
before any preprocessing runs. `data/raw` is a symlink to
`/home/naslouby/Projects/datp-shared-data/raw` (gitignored); this document
does not move or modify anything under it.

### 1.1 N-BaIoT

| Field | Value |
|---|---|
| Dataset identifier | `nbaiot` |
| Regime compatibility | A (natural, K = 9), C (synthetic Dirichlet, K = 20) |
| Raw path | `data/raw/nbaiot/` |
| Expected file types | Per-device, per-attack-family CSVs (benign + attack rows) |
| Client identity source | Filename-encoded physical device (9 devices) |
| Split type | `chronological_gapped`: sequential 60% train / 1% gap / 20% calibration / 1% gap / 18% test, per device, benign rows only, original row order preserved |
| Label columns / source | Row provenance (filename) yields benign-vs-attack-family; no in-row label column required |
| Benign/attack separation requirement | Strict; attack rows never enter train/calibration |
| Calibration eligibility requirement | n_min = 100 benign calibration rows per client; below threshold → `τ_global` fallback (Calibration-Pending) |
| Metadata feasibility requirement | None beyond filename-encoded device id |
| Hash/manifest requirement | Raw file content hash recorded before first preprocessing run; preprocessing cache keyed on hash |
| Rejection rule | N/A — device identity is filename-native |
| Expected output artifacts | Preprocessed per-device tensors; split manifest; benign train/cal/test partitions |

### 1.2 CICIoT2023

| Field | Value |
|---|---|
| Dataset identifier | `ciciot2023` |
| Regime compatibility | B-a (file-level pseudo-client, `role=boundary`), B-b (`role=rejected`) |
| Raw path | `data/raw/ciciot2023/` |
| Expected file types | Per-capture-file CSVs, d = 39 columns (re-verified against the actual processed artifact before any quantitative claim; mirror distributions vary) |
| Client identity source | Regime B-a: the file itself (63 file-defined pseudo-clients). Regime B-b: none available (see rejection rule) |
| Split type | Regime B-a: random shuffle (seeded) then sequential 70% train / 15% calibration / 15% test, benign rows only |
| Label columns / source | In-row attack-family label column; benign rows identified by label value |
| Benign/attack separation requirement | Strict; attack rows never enter train/calibration |
| Calibration eligibility requirement | Same n_min = 100 rule as N-BaIoT |
| Metadata feasibility requirement | Regime B-b requires MAC / device / IP / capture-source / timestamp columns |
| Hash/manifest requirement | Raw file content hash recorded before first preprocessing run |
| Rejection rule | Regime B-b: metadata columns absent on the available CSV artifact → emit `B_B_REJECTED_NO_METADATA` and halt; no pseudo-client substitute, no PCAP-reprocessing branch, no invented device identity (SB-28) |
| Expected output artifacts | Regime B-a: preprocessed per-file tensors; split manifest. Regime B-b: rejection record only, no split manifest |

### 1.3 Edge-IIoTset

| Field | Value |
|---|---|
| Dataset identifier | `edge_iiotset` |
| Regime compatibility | D (external validation), D-temporal (chronological recalibration) |
| Raw path | `data/raw/edge_iiotset/` |
| Expected file types | CSV with device/session identifying columns |
| Client identity source | Device-client or group-client, chosen by a first-principles feasibility audit (P6-T02); never by appeal to external precedent (SB-28) |
| Split type | Regime D: TBD by feasibility audit, benign train/cal/test. Regime D-temporal: chronological 70/30 per client by capture time |
| Label columns / source | In-row attack-type label column; benign rows identified by label value |
| Benign/attack separation requirement | Strict; attack rows never enter train/calibration |
| Calibration eligibility requirement | n_min = 100; eligibility-coverage gate requires n_k ≥ 100 for ≥ 90% of clients to proceed (else reduce K or defer) |
| Metadata feasibility requirement | Device/group identity column presence; timestamp column presence for D-temporal |
| Hash/manifest requirement | Raw file content hash recorded before first preprocessing run |
| Rejection rule | If timestamp column is absent or unsuitable, D-temporal is deferred/moved to supplement (not silently dropped); if identity metadata is absent, K is reduced or the regime is deferred, never invented |
| Expected output artifacts | Preprocessed per-client tensors; split manifest(s) (D and D-temporal); coverage-gate report |

## 2. Pipeline Artifact Contracts

For every artifact: producer stage, consumer stage(s), required manifest
fields, the reuse-validity key (identity that must match before an artifact
is reused instead of regenerated), and whether it is read-only once produced.

| Artifact | Producer | Consumers | Manifest fields | Reuse-validity key | Read-only |
|---|---|---|---|---|---|
| Raw data | External (data owner) | Preprocessing | content hash, dataset id | dataset id + content hash | Yes (never modified) |
| Preprocessed data | Preprocessing | Split builder | dataset id, preprocessing contract version, content hash | dataset id + preprocessing contract version + raw hash | Yes |
| Split manifest | Split builder | Training, scoring, evaluation | regime, client ids, split ratios, seed, row counts | dataset id + regime + split policy + seed | Yes |
| Training checkpoints (in-progress) | Training loop | Checkpoint selector | round number, dataset, regime, seed, α | dataset + regime + seed + α + round | No (mutable during training) |
| Frozen checkpoints | Checkpoint selector/freezer | Scoring, all B0–B4 policies | dataset, regime, seed, α, selected round, weight hash | dataset + regime + seed + α | Yes (read-only after freeze) |
| Calibration scores | Scoring | Threshold computation | dataset, regime, seed, checkpoint hash, client id, split=calibration | dataset + regime + seed + checkpoint hash | Yes |
| Test scores | Scoring | Metric evaluation | dataset, regime, seed, checkpoint hash, client id, split=test | dataset + regime + seed + checkpoint hash | Yes |
| Threshold artifacts | Threshold policy | Prediction generation | policy id (B0–B4, variant/comparator id), dataset, regime, seed, config hash | policy id + score artifact id + config hash | Yes |
| Prediction artifacts | Prediction generation | Metric evaluation | policy id, dataset, regime, seed, client id, threshold artifact id | threshold artifact id | Yes |
| Per-client metrics | Metric evaluation | Statistics, tables | metric name, policy id, dataset, regime, seed, client id | prediction artifact id | Yes |
| Per-seed metrics | Aggregation | Statistics | metric name, policy id, dataset, regime, seed | per-client metrics set id | Yes |
| Bootstrap summaries | Statistics | Claim gates, tables | metric name, policy pair, dataset, regime, CI method (BCa), n_boot | per-seed metrics set id | Yes |
| Paired-test summaries | Statistics | Claim gates, tables | test (Wilcoxon/Cliff's δ), policy pair, dataset, regime | per-seed metrics set id | Yes |
| Raw output tables | Table export | Curated tables | experiment id (§ naming_conventions.md), source metric/statistics artifact ids | experiment id + source artifact ids | Yes |
| Raw output figures | Figure export | Curated figures | experiment id, source metric/statistics artifact ids | experiment id + source artifact ids | Yes |
| Curated result tables | Result curation | Manuscript export | experiment id, claim tier, source raw-table id | raw table id | Yes |
| Curated result figures | Result curation | Manuscript export | experiment id, claim tier, source raw-figure id | raw figure id | Yes |
| Claim-evidence maps | Claim-gate logic | Result curation, audits | claim tier, evidence artifact ids, pass/fail status | claim id + evidence artifact ids | Yes |
| Run manifests | Every stage | Reproducibility audit | stage name, config snapshot id, inputs, outputs, timestamp, code version | stage name + config snapshot id | Yes |
| Config snapshots | Config loader | Every stage's run manifest | config group, resolved values, source file hash | config file hash | Yes |

**`results/` excludes heavy artifacts.** `results/` holds only curated tables,
curated figures, and claim-evidence maps (the last four rows above); raw
scores, checkpoints, and raw tables/figures stay under `outputs/` and
`checkpoints/` (gitignored).

## 3. `data/raw` Placement

`data/raw` is already a symlink to `/home/naslouby/Projects/datp-shared-data/raw`
and is gitignored. Expected subdirectories: `data/raw/nbaiot/`,
`data/raw/ciciot2023/`, `data/raw/edge_iiotset/`. Presence and schema are
verified at runtime by dataset loaders and recorded in manifests — not by
committed placeholder files inside the symlink target.

## Consumers

- P1-T07 manifest schema implements this contract concretely.
- P2/P6 loaders implement the dataset contracts.
- P7-T09 final audit checks every artifact class against this table.
