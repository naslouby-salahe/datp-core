# Threshold Policy Semantics

## Purpose
Protect locked threshold-policy meanings.

## When to apply
Apply when B0, B1, B2, B3, B4, B-FedStatsBenign, tau-shrink, calibration fallback, or B2-conf is touched.

## Blocking rules
Block raw protocol strings, raw protocol dicts, hidden defaults, stale names, compatibility aliases, and silent fallback for stale threshold values.

## Pass criteria
Policy state is explicit, typed where it crosses module boundaries, and tied to the same trained model and score artifacts.

## Fail criteria
Threshold meaning changes without approval, old policy names remain alive, or stress tests become causal-ladder steps.
