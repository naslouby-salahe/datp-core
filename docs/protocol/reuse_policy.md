# Reuse / Caching Principle & Raw-Data Placement

> Ticket: P0-T09. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §17; depends on [artifact_contracts.md](artifact_contracts.md). One reusable
> pipeline; a hard split between heavy stages (rerun rarely, expensively) and
> cheap stages (always reuse frozen upstream artifacts).

## Stage Classification

| Stage | Class | Rerun trigger |
|---|---|---|
| Data preparation / preprocessing | Heavy | Dataset change or preprocessing-contract change |
| Client split manifest | Heavy | Dataset change, client split change, or preprocessing-contract change |
| Model training (FedAvg / FedProx / personalized) | Heavy | Model architecture, training algorithm, dataset, or client split change |
| Checkpoint selection / freeze | Heavy | Training-algorithm or checkpoint-selection-rule change |
| Calibration/test score generation | Heavy | Score-generation contract, checkpoint, or temporal-protocol change |
| Threshold computation (B0–B4) | Cheap | Reuses frozen scores; never triggers retraining |
| Threshold variants (q, τ-shrink, cal-size, B2-conf) | Cheap | Reuses frozen scores |
| Metric evaluation | Cheap | Reuses prediction artifacts |
| Statistical analysis (bootstrap, paired tests) | Cheap | Reuses per-seed metrics |
| Mechanism analyses | Cheap | Reuses stored scores/fingerprints |
| Table export | Cheap | Reuses metrics/statistics artifacts |
| Figure export | Cheap | Reuses metrics/statistics artifacts |
| Claim mapping | Cheap | Reuses claim-gate outputs |

A threshold-only stage is never marked heavy, regardless of how many variants
or comparators it computes.

## Six Invalidation Triggers (Heavy Rerun)

A heavy stage reruns only when one of these six changes:

1. Dataset (raw content hash).
2. Client split (partition policy, ratios, or seed).
3. Preprocessing contract (feature engineering, scaling, encoding version).
4. Training algorithm (FedAvg vs FedProx vs personalization family, or its
   hyperparameter contract).
5. Model architecture (encoder/decoder shape, `input_dim` per dataset).
6. Checkpoint selection rule (round-selection policy) or, for temporal
   regimes, the temporal protocol (chronological split boundary).

Any other change — threshold policy, q, shrinkage λ, comparator, metric
definition, table layout, figure style — reuses the existing frozen
checkpoint and stored score artifacts without regenerating them.

## `data/raw` Placement (Locked)

`data/raw` is already a symlink to
`/home/naslouby/Projects/datp-shared-data/raw` and is gitignored. Expected
datasets under the symlink target: `data/raw/nbaiot/`,
`data/raw/ciciot2023/`, `data/raw/edge_iiotset/`. No dataset under `data/raw`
is moved, renamed, or modified by this repository. Presence/completeness is
verified at runtime by the owning loader (P2-T01, P6-T01, P6-T07), not
assumed.

## Enforcement

- **No hidden retraining.** A threshold-only or variant run must prove, by
  spying on the training entrypoint, that zero training calls occurred
  (P4-T08 no-retrain guard).
- **No duplicated pipelines.** One reusable pipeline serves every suite; a
  suite differs only in which stages it invokes and with which config, never
  by a parallel implementation (P7-T08 full-suite dry run proves this).
- **No stale labels.** Reused artifacts carry manifests keyed by the
  identity fields in [artifact_contracts.md](artifact_contracts.md) §2; a
  mismatch on any reuse-validity key is a hard rejection, not a silent
  overwrite (P1-T07, P7-T09).

## Consumers

- P1-T08 preprocessing cache contract implements the heavy-stage cache keys.
- P4-T08 no-retrain guard is the CI-enforced version of this document.
- P7-T09 final audit checks every heavy/cheap classification against actual
  code behavior.
