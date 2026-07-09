# Threshold-Policy & Comparator Nomenclature

> Ticket: P0-T04. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §4. Every identifier below is final. No `B5` label exists — replaced by
> `B-FedStatsBenign` / `B-LaridiFaithful`. No `B3-LGS` label exists — replaced
> by `τ-shrink` (B3 stays family-mean and is never reused for shrinkage).

## Core Ladder (B0–B4)

| ID | Definition | Role |
|---|---|---|
| B0 | Centralized AE reference: pooled benign calibration, pooled p95 threshold | Privacy-incompatible reference; **not in the FL causal ladder** |
| B1 | Client-averaged shared threshold: arithmetic mean of eligible clients' local p95 thresholds | Core ladder — shared-scope anchor |
| B2 | Per-client p95 threshold, computed on that client's own benign calibration errors | Core ladder — local-scope anchor; confirmatory comparator |
| B3 | Family-mean threshold: arithmetic mean of member clients' p95 thresholds within a device-taxonomy family | Core ladder — mechanism baseline; **Regime A only** (requires a taxonomy) |
| B4 | k-means cluster-mean threshold on the 4-scalar fingerprint `[µ_e, σ_e, skew_e, p95(e)]` | Core ladder — cluster mechanism; **canonical K = 3**; K = 9 and other K are exploratory/supplementary only (SB-32) |

**B4 fingerprint (locked, per client).** `[mean(reconstruction_error),
std(reconstruction_error), skewness(reconstruction_error),
p95(reconstruction_error)]`, standardized (zero mean, unit variance per
feature) before k-means (Euclidean distance).

## Threshold Variants (Supportive, Outside Core Ladder)

| ID | Definition | Role |
|---|---|---|
| τ-shrink (LGS) | Local-global shrinkage: `τ_k(λ) = λ·τ_k,p95 + (1−λ)·τ_global` | Supportive threshold variant |
| Calibration-size-aware fallback | Size-dependent `λ(n_k)` replacing the hard `n_min = 100` fallback | Supportive threshold variant |
| B2-conf | Split/federated-conformal variant of B2 at marginal coverage `1−α`, `α = 1−q` | Supportive threshold variant; closes the tautology critique (L04) |

## Comparators

| ID | Definition | Role |
|---|---|---|
| `B-FedStatsBenign` | DATP-compatible **benign-only** federated summary-statistics threshold at the matched-exceedance operating point | Comparator primitive / matched threshold comparator |
| `B-LaridiFaithful` | Relaxed Laridi reproduction using **normal and anomalous** validation summaries | **Out of scope** — violates the benign-only contract (SB-29); named disclosure only, never computed inside DATP's benign-only threshold contract |

## Stress-Test Comparators (Outside Causal Ladder)

| ID | Definition | Role |
|---|---|---|
| FedProx | Heterogeneity-aware aggregation encoder, µ-grid frozen before results | External stress test |
| Ditto | Personalized local AE regularized toward the global model (proximal µ) | External stress test; used **only if faithfully implemented** |
| `FedRep-AE` / `FedPer-AE` | Shared-representation / local-head personalization fallback adapted to the DATP AE | External stress test; used when Ditto is not faithfully implemented; **never labeled "Ditto"** (SB-24) |

## Naming Locks

- `B-FedStatsBenign` / `B-LaridiFaithful` replace any prior `B5` label.
- `τ-shrink` / LGS replaces any prior `B3-LGS` label; B3 remains family-mean
  and must not be reused for shrinkage.
- The model-personalization fallback is never labeled "Ditto" unless the true
  Ditto algorithm is implemented (SB-24).
- B4 canonical K = 3, pre-committed before results; K = 9 and other K are
  exploratory (SB-32).
- `B-FedStatsBenign` uses the **full pooled variance** including the
  between-client mean-shift term, never the simple pooled-variance formula
  (SB-26): `σ²_global = Σ n_k·[σ_k² + (µ_k − µ_global)²] / Σ n_k`. The main
  comparison is the matched-exceedance operating point; fixed-k
  (`k ∈ {2.0, 2.5, 3.0}`) is supplementary sensitivity only (SB-27).

## Consumers

- `ThresholdPolicy` enum (P1-T02): `B0 | B1 | B2 | B3 | B4`.
- `Comparator` enum (P1-T02): `TAU_SHRINK | CAL_SIZE_AWARE | B2_CONF |
  B_FEDSTATS_BENIGN | B_LARIDI_FAITHFUL_DISCLOSURE | FEDPROX | DITTO |
  FEDREP_AE | FEDPER_AE`.
- P3 policy implementations (B0–B4) and P4 comparator implementations.
