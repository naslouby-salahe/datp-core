# Config, Experiment-Suite & Experiment-ID Naming Conventions

> Ticket: P0-T06. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §9. Every table/figure traces back to one experiment ID; every experiment ID
> belongs to exactly one suite; every suite is built from named config groups.
> Depends on [claim_hierarchy.md](claim_hierarchy.md),
> [regimes.md](regimes.md), [policies.md](policies.md).

## 1. Config Groups

| Group | Directory | Contents |
|---|---|---|
| Datasets | `configs/datasets/` | `nbaiot.yaml`, `ciciot2023_file_level.yaml`, `ciciot2023_rejected_b_b.yaml`, `edge_iiotset.yaml` |
| Training | `configs/training/` | `base_autoencoder.yaml`, `fedavg_nbaiot.yaml`, `fedavg_edge_iiotset.yaml`, `fedprox_nbaiot.yaml`, `fedprox_edge_iiotset.yaml`, `personalized_ae.yaml` |
| Thresholding | `configs/thresholding/` | `core_ladder.yaml`, `b_fedstats_benign.yaml`, `quantiles.yaml`, `shrinkage.yaml`, `calibration_size.yaml`, `calibration_size_shrinkage.yaml`, `conformal_b2.yaml` |
| Analysis | `configs/analysis/` | `statistics.yaml`, `mechanisms.yaml`, `absorption.yaml`, `reporting.yaml` |
| Suites | `configs/suites/` | `confirmatory_regime_a.yaml`, `regime_c_dirichlet.yaml`, `external_validation_regime_d.yaml`, `threshold_variants.yaml`, `stress_tests.yaml`, `temporal_recalibration.yaml`, `full_journal.yaml` |

A suite config composes dataset + training + thresholding + analysis configs
by reference; it never inlines their values.

## 2. Config-Key Naming Rules

- No raw policy strings in config values where an enum exists. Threshold
  policy, comparator, regime, and claim-role fields are enum-backed
  (`ThresholdPolicy`, `Comparator`, `Regime`, `ClaimRole` — P1-T02), not
  free-text strings.
- `personalized_ae.yaml` never hardcodes `"Ditto"` as a key or value; the
  fallback is `FedRep-AE` / `FedPer-AE`, named as such (SB-24).
- `b_fedstats_benign.yaml` locks the full pooled-variance + matched-exceedance
  contract (SB-26/SB-27) before any computation; no post-hoc tuning keys.
- No config key encodes a stale label (`B5`, `B3-LGS`) — see
  [policies.md](policies.md) naming locks.

## 3. Experiment-ID Registry

Every ID below is unique and maps to exactly one suite.

| ID | Purpose | Suite | Tier |
|---|---|---|---|
| E-C1 | B1 vs B2 threshold-scope effect (confirmatory) | `confirmatory_regime_a` | 1 |
| E-S1 | Construction-sensitivity (mean-artifact rule-out) | `confirmatory_regime_a` | 2 |
| E-S2 | q-sensitivity sweep | `threshold_variants` | 2 |
| E-S3 | Dirichlet severity sweep | `regime_c_dirichlet` | 2 |
| E-M1 | Cluster/family granularity + stability | `confirmatory_regime_a` | 5 |
| E-M2 | B4 cluster-feature ablation | `confirmatory_regime_a` | 5/7 |
| E-M3 | Per-client CDF overlays + Ennio deep dive | `confirmatory_regime_a` | 5 |
| E-M4 | JS-divergence ↔ gain regression | `confirmatory_regime_a` | 5 |
| E-M5 | Threshold-shift vs ΔFPR/ΔTPR surface | `confirmatory_regime_a` | 5 |
| E-V1 | Calibration-size sweep | `threshold_variants` | 6 |
| E-V2 | Local-global shrinkage (τ-shrink) | `threshold_variants` | 6 |
| E-V3 | Split-conformal B2-conf | `threshold_variants` | 1-support |
| E-X1 | Edge-IIoTset external validation | `external_validation_regime_d` | 3 |
| E-T1 | FedProx aggregation stress test | `stress_tests` | 4 |
| E-T2 | Model-personalization stress test | `stress_tests` | 4 |
| E-T3 | `B-FedStatsBenign` matched comparator | `stress_tests` | 4 |
| E-B1 | Temporal recalibration MVE | `temporal_recalibration` | 6 |
| E-O1 | Operational alert burden | `confirmatory_regime_a` | 5-support |
| E-Q1 | Federated quantile-estimation backbone | `full_journal` | 7 |
| E-Q2 | Robust cluster-median B4 variant | `full_journal` | 7 |
| E-Q3 | Equity suite (Jain / Gini / IQR) | `full_journal` | 7 |
| E-Q4 | Bootstrap CIs + Wilcoxon/Cliff's δ for all secondary metrics | `full_journal` | 7 |
| E-Q5 | Fixed-k Laridi sensitivity | `full_journal` | 7 |
| E-Q6 | Bytes-per-round communication/storage table | `full_journal` | 7 |

`full_journal` composes every suite above; it is the complete run, not an
additional experiment family.

Suppressed/rejected items (E-R1…E-R8, roadmap §9.4) are not suite members;
they are recorded as rejection notes only (see
[regimes.md](regimes.md), [reuse_policy.md](reuse_policy.md)).

## Consumers

- P1-T04 typed config schemas load these groups.
- P6/P4 suite configs are authored against this registry.
- P7-T05 claim-evidence map cross-references experiment IDs to claim tiers.
