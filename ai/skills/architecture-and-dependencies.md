# Skill: architecture-and-dependencies

## Trigger

A new import, a new type/module placement, or a dependency change.

## Checks

- **Layer direction.** Every import respects the layer dependency diagram across `domain`,
  `application`, `config`, `analysis`, `infrastructure`, `composition`, `cli`. No forbidden edge, direct
  or routed through an intermediate module. Enforced by `uv run lint-imports` and
  `uv run pytest -m architecture`; both must pass and are not interchangeable.
- **Framework confinement.** PyTorch, Flower, scikit-learn, SciPy, pandas, NumPy, and Pydantic never
  appear in `domain`, `application`, `config`, or the scientific parts of `analysis`. A relaxed
  import-linter/archon contract requires an approved diagram change, never a silent carve-out.
- **Placement.** A new type goes in exactly one layer by the ordered questions (scientific meaning →
  orchestration → configuration → reporting → framework need → wiring → entrypoint). If two layers
  remain plausible, record a tie-breaker; do not place by convenience.
- **Dependencies.** Every declared dependency is in the accepted table and its purpose-scoped group;
  numerically/order-sensitive libraries (scikit-learn, PyArrow, NumPy, SciPy, blake3, msgspec, PyTorch,
  Flower) are exact-pinned; the committed `uv.lock` is the reproducibility anchor and is not
  regenerated without a documented reason. No rejected-category dependency (Hydra, OmegaConf, Ray, Dask,
  Celery, an ORM, a DAG engine, a DI/plugin framework) is added without a recorded justification.
- **Official-library-first.** Prefer a clear standard/official-library path over avoidable custom
  parsing, validation, statistics, formatting, or CLI boilerplate; otherwise state why custom code is
  required.

## Fail conditions

A new import creates a forbidden edge, a framework leaks outside its layer, a numerically-sensitive
dependency is unpinned, or a rejected dependency appears without a recorded disposition.

## On failure

Fix the import to respect the diagram or report a blocker if the required direction does not exist —
never add a contract exception silently.
