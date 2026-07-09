# Seed Plan

> Ticket: P0-T07. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §3, §10. Depends on [claim_hierarchy.md](claim_hierarchy.md) (Tier 1 requires
> 10 paired seeds).

## Locked Seed Set

10 seeds, fixed before any result is observed: `{0, 1, 2, 3, 4, 5, 6, 7, 8, 9}`
(literal seed values are assigned once by P1-T03 and never reselected after
seeing a result).

## Pairing Rule

For a given seed `s`, B1 and B2 (and B0, B3, B4) reuse the **identical**
frozen AE state, seeds, and per-client score artifacts for that `s` within a
(dataset, regime, α) ladder. The per-seed delta is computed only between
policies that share the same seed and the same frozen checkpoint:

`Δ_s = CV(FPR)[B1, s] − CV(FPR)[B2, s]`

Comparing metrics across different seeds, or across unfrozen/refit
checkpoints, is never a valid pairing.

## 5-Seed Preliminary vs 10-Seed Main

- The first 5 seeds (`{0, 1, 2, 3, 4}`) may run as a preliminary check.
- The 10-seed result is the confirmatory evidence (Tier 1). The 5-seed result
  is never substituted for it and is labeled preliminary wherever shown.

## Seed-Extension Honesty Rule (Locked)

- If the 10-seed extension widens the CI or brings it near zero, the 10-seed
  result becomes the main result; the 5-seed conference result is labeled
  preliminary.
- If the reproduced 5-seed CI differs materially from the reference
  `[0.647, 0.769]` — shifting toward zero, or more than ~20% wider than the
  reference width (≈0.122, i.e. wider than ≈0.147) — expansion claims are
  blocked until resolved.
- The 10-seed result is never suppressed when it is less favorable than the
  5-seed result (SB-21).

## No Seed Dropping

No seed is dropped, excluded, or re-rolled after observing its result. A seed
that fails to converge or produces an ineligible-client cascade is reported as
a documented anomaly, not silently removed from the paired set.

## Consumers

- P1-T03 `SeedPlan` types encode the 10 literal seed values and the pairing
  rule.
- P2-T09 anchor evaluation wires the paired-delta computation.
- P7-T03 statistical finalization audits seed-count and pairing compliance.
