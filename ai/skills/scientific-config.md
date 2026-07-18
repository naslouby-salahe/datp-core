# Skill: scientific-config

## Trigger

Adding or changing a scientific/execution value, a `config/schemas/` or `config/mapping/` file, a
seed path, or a batch/chunk/checkpoint profile.

## Checks

- **Never invent a value.** A missing scientific or execution value is a blocker.
- **Single canonical owner.** A scientific/execution value has exactly one named owner across the
  repository; `config/schemas/`, `config/mapping/`, `domain/`, and `infrastructure/` never redeclare
  the same value (or its literal) under any name — other modules import the owner.
- **Config-worthy values are validated and YAML-backed.** A genuine parameter or choice has a
  `config/schemas/` field, a pure `map_*(schema) -> DomainSpec` mapper in `config/mapping/`, and a
  `configs/` YAML entry. A locked invariant instead uses a typed `Literal[...]` schema field plus a
  domain-level `__post_init__` check against one canonical `Final` constant; it is never hidden from
  config entirely. A pure formula or cited locked invariant is exempt from YAML backing.
- **Mapping is pure and one-directional.** No side effects, no framework calls, no I/O; no Pydantic
  model or raw YAML mapping crosses past the mapping boundary into `application`/`domain`/`analysis`;
  no default the schema did not declare.
- **Discriminated tags, not flags.** A variant is a closed enum/union, never a boolean combination or
  inferred from which optional fields are set. `EvaluationConfig.primary` is `CV_FPR`; AUROC appears
  only among controls. A confirmatory `StatisticalConfig` sets BCa, 0.95 confidence, 10 paired seeds,
  explicit resample count.
- **Seeds are deterministic.** Every seed derives from a typed `SeedPlan`/`Seed`, reproducible from
  tracked config; no scattered global seeding, no seed identity from list position.
- **Fixed batch/chunk profiles.** No automatic batch/chunk-size reduction under memory pressure;
  resource pressure may only pause or fail a stage, never mutate its profile. A recovery checkpoint is
  reused only after verifying execution-profile compatibility.
- **Feasibility gates are evidenced.** A pass records eligible/total counts, coverage, and the locked
  minimum; a rejection carries a typed reason. Missing evidence is not a pass.

## Fail conditions

A value is invented, redeclared, hidden from config, mapped with a side effect, or a batch size is
auto-reduced.

## Output

State which schemas/mappings/YAML changed, which values map to which owner, and any remaining risk.
