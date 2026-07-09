# Regime Definitions

> Ticket: P0-T03. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §7, §11. Each regime carries a fixed `role` and a `pass_rule`. Roles are not
> interchangeable: a regime with `role=boundary` never receives a
> confirmatory-style quantitative claim.

## Regime A — N-BaIoT natural physical-device split

- **Role:** `confirmatory` (sole confirmatory regime).
- **Dataset / clients:** N-BaIoT, 9 physical devices (K = 9).
- **Purpose:** Confirmatory B1 vs B2; backbone for B0–B4 + all threshold
  variants and mechanism modules.
- **Primary metric:** CV(FPR).
- **Pass / fail / suppression rule:** Pass iff the 10-seed BCa CI on
  Δ = CV(FPR)[B1] − CV(FPR)[B2] excludes zero, positive direction. Revise
  honestly otherwise (never suppressed).
- **Placement:** Main paper.

## Regime B-a — CICIoT2023 file-level pseudo-client boundary

- **Role:** `boundary`.
- **Dataset / clients:** CICIoT2023 file-level (d = 39, re-verified against
  the processed artifact before any quantitative claim — mirror distributions
  differ in column count), 63 file-defined pseudo-clients.
- **Purpose:** Near-homogeneous applicability boundary, not a natural
  physical-device regime.
- **Threshold policies:** B0, B1, B2, B4.
- **Primary metric:** CV(FPR); pairwise JS divergence.
- **Pass / fail / suppression rule:** A null result is reported strictly as an
  applicability boundary (SB-16); never generalized to CICIoT2023 as a whole;
  carries no confirmatory-style metric row.
- **Placement:** Main paper (boundary section).

## Regime B-b — CICIoT2023 device/MAC repartition

- **Role:** `rejected`.
- **Status label:** `B_B_REJECTED_NO_METADATA`.
- **Rejection rule:** The available CSV artifact lacks MAC / device / IP /
  capture-source / timestamp columns; there is no pseudo-client substitute and
  no PCAP-reprocessing branch (out of scope). Device identity must never be
  invented (SB-28).
- **Quantitative claim:** None. B-b never carries a metric row (SB-23); it is
  a suppression note only.
- **Placement:** Suppression note.

## Regime C — N-BaIoT synthetic Dirichlet severity sweep

- **Role:** `supportive`.
- **Dataset / clients:** N-BaIoT, 20 synthetic Dirichlet clients,
  α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}.
- **Purpose:** Heterogeneity-severity gradient support for the B1→B2 gain.
- **Threshold policies:** B1, B2, B4.
- **Primary metric:** CV(FPR) delta vs α.
- **Pass / fail / suppression rule:** Report gain vs α; overlapping low-α seed
  ranges are reported as a high-heterogeneity band, not strict monotonicity.
- **Placement:** Main paper.

## Regime D — Edge-IIoTset external validation

- **Role:** `external_validation`.
- **Dataset / clients:** Edge-IIoTset; device-client or group-client, decided
  by a first-principles feasibility audit (P6-T02), never by appeal to
  external precedent (SB-28).
- **Purpose:** External generalization of the threshold-scope effect.
- **Threshold policies:** B1–B4 + `B-FedStatsBenign` + q-sensitivity.
- **Primary metric:** CV(FPR) + BCa CI.
- **Pass / fail / suppression rule:** Eligibility-coverage gate: proceed only
  if n_k ≥ 100 for ≥ 90% of clients; else reduce K or defer (fallback §12.9).
- **Placement:** Main paper.

## Regime D-temporal — Edge-IIoTset chronological recalibration

- **Role:** `boundary` (temporal, exploratory framing).
- **Dataset / clients:** Same clients as Regime D, chronological 70/30 split
  (train + calibrate on first 70% of each client's benign data by capture
  time; evaluate on the last 30%).
- **Purpose:** One-shot recalibration temporal MVE (minimum viable
  experiment). N-BaIoT drift magnitude is limited and is not used; CICIoT2023
  temporal probing is rejected (`TEMPORAL_REJECTED_NO_TIMESTAMPS`, no
  timestamp column and no pseudo-time substitute).
- **Threshold policies:** B1, B2, B4; frozen vs one-shot recalibration.
- **Primary metric:** Per-window CV(FPR); recovery ratio.
- **Pass / fail / suppression rule:** Exactly one of three pre-specified
  outcomes applies (roadmap §11.1): Outcome A (recovery ≥ 50%, recalibration
  helps), Outcome B (recovery < 50%, temporal fragility), Outcome C (drift
  within the static-split bootstrap CI, no meaningful drift). No streaming
  detector is added retroactively.
- **Placement:** Main paper, or supplement if timestamps prove unsuitable.

## Rejected Status Labels (Reserved)

- `B_B_REJECTED_NO_METADATA` — Regime B-b, see above.
- `TEMPORAL_REJECTED_NO_TIMESTAMPS` — CICIoT2023 temporal probing (E-R2).

## Consumers

- `Regime` enum (P1-T02): `A | B_A | B_B_REJECTED_NO_METADATA | C | D |
  D_TEMPORAL`.
- P6 loaders and feasibility/rejection guards (P6-T02, P6-T04, P6-T08).
