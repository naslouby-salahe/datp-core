# Configuration Hook

## Trigger
After any edit touching a configuration schema, mapping function, or resolved specification, or introducing or modifying a scientific or execution constant anywhere in the codebase.

## Purpose
Keep configuration validation, mapping, and fingerprinting free of hidden defaults and ambiguous variants.

## Blocking status
Blocks completion.

## Required checks
- No hidden default, no silent environment override, no untyped configuration merging, and no ambiguous override precedence; `config/compose.py`'s single declared precedence is the only resolution path.
- A discriminated tag (closed union/enum) is used wherever a variant exists; no boolean-flag combination stands in for a variant (for example no `use_full_pooled_variance` or tie-break boolean).
- `EvaluationConfig.primary` is `CV_FPR`; AUROC, if present, appears only among `controls` with `is_control` true.
- A confirmatory experiment's `StatisticalConfig` sets `BCA_BOOTSTRAP`, 0.95 confidence, and ten paired seeds; `BootstrapResampleCount` is always explicit, never defaulted.
- Scientifically distinct stages keep separate fingerprints; only scientific configuration and the output-affecting subset of execution configuration enter a stage fingerprint.
- No Pydantic model or raw YAML mapping crosses past the mapping boundary into application execution.
- A scientific or execution value has exactly one canonical named owner across the repository; `config/schemas/`, `config/mapping/`, and any `domain/` or `infrastructure/` constant never independently redeclare the same value under a different name.

## Failure behavior
Stop the edit and report the exact configuration violation; never add a default or precedence rule not already declared by the schema.
