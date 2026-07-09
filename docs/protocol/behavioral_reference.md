# Behavioral Reference (DATP Conference Project)

> Ticket: P0-T10. `/home/naslouby/Projects/datp` is consulted **only** for the
> mathematical/behavioral semantics below. This document records behavior,
> not source, layout, or module names, and implies no dependency on that
> project's code. `datp-core` is written from scratch (roadmap §17).

## 1. B2 — Per-Client p95 Threshold

Each eligible client's threshold is the q-quantile (default `q = 0.95`) of its
own benign calibration reconstruction errors, using linear-interpolation
percentile estimation: `τ_i = percentile(E_i, q·100)`, no alternative
interpolation method.

## 2. B1 — Client-Averaged Shared Threshold

Unweighted arithmetic mean of the per-client local p95 thresholds, over
eligible clients only — never sample-size weighted (weighting would confound
the shared-vs-local comparison): `τ_global = (1/K_elig) · Σ τ_i`.

## 3. B3 / B4 — Family-Mean and Cluster-Mean Thresholds

**B3.** Arithmetic mean of member clients' p95 thresholds within a
device-taxonomy family, restricted to Regime A (requires a taxonomy):
`τ_f = (1/|elig∩f|) · Σ τ_i`.

**B4 fingerprint.** Per eligible client, the 4-scalar vector
`[mean(E_i), std(E_i, ddof=1), skewness(E_i), p95(E_i)]` (std = 0 for n < 2;
skewness clamped to 0 if non-finite/constant). Fingerprints are standardized
(zero mean, unit variance per feature) before k-means clustering (Euclidean
distance). K is fixed for Regime A (canonical K = 3, per
[policies.md](policies.md)); for other regimes K may be selected by
maximizing silhouette score over a candidate grid with a fixed random seed.
The cluster threshold is the arithmetic mean of member clients' p95
thresholds.

## 4. Eligibility (`n_min`) and Fallback

`n_min = 100` benign calibration samples per client. A client with fewer than
`n_min` benign calibration samples is "Calibration-Pending": it never enters
local threshold or fingerprint computation and instead receives `τ_global`
(the B1 shared threshold) unconditionally, under every policy (B1–B4).
Coverage is reported as `|K_elig| / |K|`.

## 5. CV(FPR)

`CV(FPR) = std(FPR, ddof=1) / mean(FPR)`, computed only over eligible
clients. Undefined (not computed) with fewer than 2 eligible clients or a
zero mean FPR.

## 6. Benign-Only Calibration/Test Split Semantics

Calibration and threshold fitting use benign data exclusively; attack data
never enters threshold computation at any point in the reference behavior.
Benign rows are split per client into train / calibration / test partitions;
splits are either chronological (sequential, order-preserving, with small
buffer gaps between adjacent partitions to reduce autocorrelation leakage) or
seeded-random-then-sequential, depending on dataset — see
[artifact_contracts.md](artifact_contracts.md) §1 for the per-dataset split
type locked for `datp-core`.

## 7. Checkpoint Protocol

One shared FedAvg autoencoder checkpoint is trained per (dataset, regime,
seed, α) and reused, without retraining, by every threshold policy (B0–B4)
evaluated on that key. Training runs to a bounded round budget with a
convergence diagnostic (relative change in aggregated benign validation loss
below a small tolerance over a trailing window); convergence is logged, not
used to early-stop or to select which run "worked." Once selected, a
checkpoint is frozen and not further trained.

## 8. AUROC Role

AUROC is computed from benign-vs-attack scores strictly as a diagnostic /
model-quality control (and, at most, a coarse sanity gate on the encoder). It
is never an input to threshold derivation and never selects a threshold
policy or comparator.

## Consumers

- P3 policy implementations (B0–B4) reproduce §1–§3 exactly.
- P2-T04 split-semantics implementation reproduces §6.
- P2-T06/T07 training/freeze implementation reproduces §7.
- P3-T09 AUROC-control tests assert §8.
