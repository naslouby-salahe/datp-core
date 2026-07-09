# Experiment Readiness Check

## Purpose
Verify an experiment is ready before execution.

## When to apply
Apply before changing or running configs, runners, seeds, metrics, output paths, or artifacts.

## Blocking rules
Block ambiguous dataset role, client definition, seed list, config completeness, output layout, metric direction, artifact provenance, legacy config keys, old output names, and hidden defaults.

## Pass criteria
Dataset, clients, seeds, metrics, configs, outputs, and provenance are explicit and current.

## Fail criteria
Readiness is incomplete, old and new layouts coexist, or experiment execution would create unclear artifacts.
