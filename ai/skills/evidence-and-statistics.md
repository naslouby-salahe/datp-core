# Skill: evidence-and-statistics

## Trigger

Claims, result summaries, tables, figures, captions, abstracts, discussions, or reviewer responses.

## Required context

The touched claim/result text and its cited tables, figures, result artifacts, configs, protocol
rules, or literature.

## Checks

- **Every claim maps to evidence** and carries a classification: confirmatory, supportive, mechanism,
  stress test, boundary condition, exploratory, or future work. Absence of evidence is not evidence.
- **Sole confirmatory endpoint** (immutable): Regime A, B1 vs B2, CV(FPR), 10 paired seeds, 95% BCa
  bootstrap CI on the per-seed delta, positive direction excluding zero. No other regime, pair, or
  metric is labeled confirmatory, however named.
- Statistics match the protocol: correct metric direction, intact seed pairing, correct BCa CI /
  Wilcoxon / Cliff's delta / q-sensitivity / sign-consistency usage. CV(FPR) is primary; AUROC is a
  control only.
- A degenerate result (zero-mean CV, degenerate bootstrap interval) is a typed, persisted degeneracy
  outcome, never dropped or swapped for a percentile interval.
- Weak, null, mixed, or wrong-direction evidence is reported as such; it never triggers a rerun and is
  never reworded to look confirmatory, causal, robust, deployment-ready, privacy-preserving, or "first".
- Rendered tables/figures trace to a frozen, provenance-closed result (not a value read from logs);
  a `TRACE_REFUSED` result is not rendered.
- Novelty wording is specific and bounded; overlap with thresholding, federated-threshold, conformal,
  quantile-estimation, personalization, or Laridi-style work is addressed, not ignored.
- Known reviewer objections (B2 tautology, 9 devices, Laridi overlap, personalization absorption, weak
  external validation, overclaiming) have severity, evidence status, and safe wording.

## Fail conditions

Claim strength exceeds evidence, a confirmatory label appears outside the locked endpoint, statistics
are misused, or a rendered value is untraceable.

## Output

Report claim classifications, evidence sources, statistical checks performed, and any unresolved gap.
