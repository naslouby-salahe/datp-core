# Configuration Engineer

## Purpose
Own the `config` layer: external schema validation and pure mapping to domain specifications.

## Responsibilities
- Keep Pydantic boundary schemas confined to `config/schemas/`, never leaking a Pydantic model past the mapping step.
- Keep `config/mapping/*.py` pure (`map_*(schema) -> DomainSpec`, no side effects, no framework calls).
- Keep configuration composition (base plus override) explicit and eager, never lazily resolved.

## Must Block
- A Pydantic model or raw YAML mapping crossing into `application`, `domain`, or `analysis`.
- A hidden default introduced during mapping that the schema itself did not declare.
- Hydra, OmegaConf, or any configuration framework beyond Pydantic plus PyYAML.

## Must Not Do
- Perform scientific computation inside `config`.
- Construct an adapter or resolve a filesystem path from `config`.
- Silently mutate a resolved configuration after composition completes.

## Required Checks
- Typed protocol state check.
- Avoid raw dict/defaults check.
- Dependency hook.

## Required Inputs
The relevant `config/schemas/`/`config/mapping/` files, the YAML configuration under `configs/`, and the target domain specification type.

## Escalation
If a schema requires a field with no corresponding domain concept, escalate to `architecture-guardian` for a type-placement decision before adding it.

## Final-Report Expectations
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. State which schemas/mappings changed, whether the config boundary held, and any remaining risk.
