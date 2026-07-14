# Naming Hook

## Trigger
After edits.

## Purpose
Keep naming clear, current, and semantically accurate.

## Blocking status
Blocks completion.

## Required checks
- No weird names, vague variables, stale labels, unclear config keys, misleading class names, overloaded terminology, or old names kept as aliases.
- No class named the bare word `Data`, `Config`, `Result`, `Manager`, `Context`, `Payload`, `Handler`, or `Processor`; a result type is named per operation (for example `PolicyEvaluationResult`, not `Result`).
- Every `StrEnum` member is `UPPER_SNAKE` with a snake_case serialized value.
- A configuration schema type is named `<Section>Config`; the domain specification it maps to is named `<Concept>Spec`.
- A test module is named `test_<behavior>.py`, describing the behavior under test, not the implementation detail.

## Failure behavior
Rename inside approved scope and update direct references.
