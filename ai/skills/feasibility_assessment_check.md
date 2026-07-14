# Feasibility Assessment Check

## Purpose
Keep feasibility gates evidence-based rather than assumed.

## When to apply
Apply whenever a `RegimeDFeasibilityResult`, `RejectionRecord`, or feasibility-gate decision is added or changed.

## Blocking rules
Block a feasibility pass recorded without meeting the locked minimum-evidence threshold, a rejection reason left unrecorded, and a suppressed or missing-evidence case treated as passing.

## Pass criteria
A feasibility result states its eligible/total counts, coverage, and locked minimum evidence explicitly, and a rejection carries a typed `RejectionReason`.

## Fail criteria
A feasibility gate passes without meeting its recorded threshold, or missing evidence is treated as silently acceptable.
