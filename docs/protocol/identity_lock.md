# Scientific Identity Lock

> Ticket: P0-T01. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §2–§3. This document is the single import point for identity assertions used
> by later contracts, enums, and tests. It restates the roadmap; it does not
> reinterpret it.

## Locked Identity Statements

1. **Fixed encoder / fixed federated model.** The trained autoencoder is fixed
   for the core B1–B4 ladder. The same final AE state, seeds, and per-client
   score artifacts are reused across B1–B4 without retraining, within a given
   dataset/regime/baseline ladder. `input_dim` differs across datasets
   (SB-13); the fixed-encoder constraint does not cross datasets.
2. **FedAvg is the main training baseline** for the core causal ladder (E=1,
   full participation).
3. **Sole causal variable.** Threshold-calibration scope is the sole
   experimental variable in the causal ladder (B0 excluded, see below).
4. **Benign-only calibration.** Attack data is reserved for evaluation and is
   never used to fit or tune a threshold.
5. **Primary operating-point concern.** Per-client FPR disparity, not global
   F1, AUROC, or accuracy.
6. **AUROC is a control.** AUROC is a model-quality sanity/control metric, not
   the primary thresholding verdict.
7. **Scope discipline.** The journal extension strengthens DATP but must not
   become a generic FL-IDS benchmark paper.
8. **Stress tests stay outside the ladder.** FedProx, model personalization,
   and Laridi-style comparators remain outside the causal threshold-scope
   ladder and are never presented as sharing its experimental control.
9. **Out of scope.** Dynamic DATP, poisoning, privacy guarantees, deployment
   profiling, backdoor, evasion, and full drift detection are out of scope;
   any mention is explicitly future work or a spin-off.
10. **B0 is not in the FL causal ladder.** B0 is a centralized, privacy-
    incompatible reference used for context only.

## Fairness Definition (Locked)

Every use of "fairness" means **operational / service-level FPR equity** — the
evenness of false-alarm burden across client devices. It never refers to
protected-attribute or human fairness. Stated once, enforced everywhere.

## Scope Boundaries

The enumerated, testable SB-01…SB-32 list lives in
[scope_boundaries.md](scope_boundaries.md).

## Consumers

- P1-T02 domain enum docstrings cite this document.
- P7 audits assert against the identity statements above.
