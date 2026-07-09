# Scope Boundaries (SB-01…SB-32)

> Ticket: P0-T01. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §16. Each ID appears exactly once, in order, as a `SB-NN.` prefixed bullet so
> `tests/unit/test_scope_boundaries.py` can parse and count them mechanically.

- SB-01. Do not submit to Computers & Security (standing AI/ML + FL scope moratorium).
- SB-02. Do not add FedBN (encoder has no BatchNorm; adding it breaks the fixed-encoder identity).
- SB-03. Do not add more than one new IoT dataset (Edge-IIoTset).
- SB-04. Do not add more than three stress-test comparator families (FedProx; one model-personalization; one benign-only Laridi-style).
- SB-05. Do not claim DATP "solves" non-IID FL.
- SB-06. Do not claim improved global Macro-F1; P10 Macro-F1 degradation is a reported negative.
- SB-07. Do not claim privacy preservation without formal DP/SecAgg.
- SB-08. Do not claim concept-drift handling; the temporal probe is one-shot recalibration only.
- SB-09. Do not add adversarial robustness, poisoning, backdoor, or evasion experiments.
- SB-10. Do not add hardware or edge profiling.
- SB-11. Do not add streaming drift-detection frameworks.
- SB-12. Do not add Byzantine-robust federated conformal prediction.
- SB-13. Do not change the mainline AE architecture, FedAvg aggregator, or round budget within a dataset ladder; `input_dim` is matched per dataset; the fixed-encoder constraint applies within each dataset/regime/baseline ladder, not across datasets.
- SB-14. Do not reuse conference figures verbatim.
- SB-15. Do not silently change the CV(FPR) definition.
- SB-16. Do not generalize the CICIoT2023 file-level null; it stays Regime B-a.
- SB-17. Do not cite FedMSE (COSE 2025) as evidence COSE accepts FL today.
- SB-18. Do not target FGCS as a primary venue.
- SB-19. Do not use a Sankey diagram for B4 interpretability at K = 3/9; use a contingency table or small heatmap.
- SB-20. Do not present hypothetical alert/day numbers as measurements; use a real/cited rate or omit the metric.
- SB-21. Do not suppress the 10-seed result when less favorable; apply the CI-discrepancy rule.
- SB-22. Do not tune the `B-FedStatsBenign` protocol after seeing results; it is locked before computation.
- SB-23. Do not claim Regime B-b under any `B_B_REJECTED_*` status; do not collapse MAC-based and group-based partitions into one label.
- SB-24. Do not call the model-personalization fallback "Ditto"; use `FedRep-AE`/`FedPer-AE`, clearly labeled.
- SB-25. Do not present FedProx / model-personalization / Laridi-style results as part of the core B1–B4 causal ladder.
- SB-26. Do not use the simple pooled-variance formula for `B-FedStatsBenign`; use the full pooled variance including the between-client mean-shift term.
- SB-27. Do not use any fixed k as the primary `B-FedStatsBenign` comparator; the main comparison is the matched-exceedance operating point; fixed-k is supplementary.
- SB-28. Do not appeal to any unverified precedent to justify a dataset partition; partitioning is decided by first-principles feasibility audits.
- SB-29. Do not call a benign-only Laridi adaptation "faithful"; `B-LaridiFaithful` is reserved for the anomaly-labeled variant only.
- SB-30. Do not claim fleet-scale validation (K > 100).
- SB-31. Do not use Plassier et al. as the primary federated-conformal anchor; primary anchor is Lu et al. (ICML 2023), co-anchor Humbert et al. (ICML 2023).
- SB-32. Do not lock B4 K post-hoc; canonical K = 3; K = 9 and other K are exploratory/supplementary.

## Forbidden Claim Terms

The following phrases never appear as an achieved-result claim anywhere in
`docs/`, `results/`, or manuscript exports: "solves non-IID", "privacy-
preserving", "concept-drift handling" (beyond one-shot recalibration),
"fleet-scale validated", "first to" / "novel" without independent
verification.
