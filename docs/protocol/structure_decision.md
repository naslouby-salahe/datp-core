# Repository Structure Decision

> Ticket: P0-T11. Ratifies `MASTER_TICKET_LOG.md` §5. The roadmap-suggested
> tree was audited against `AGENTS.md`/`ai/` governance and the existing repo
> state (the `data/raw` symlink, the pre-existing `ai/`, `docs/`, `.claude/`,
> `.codex/`, `.agents/`, `.github/` governance surfaces).

## Verdict

Accept the `configs/ · src/datp_core/ · tests/ · scripts/` backbone and the
`outputs/results/checkpoints` separation. Reject all release/versioning
artifacts. Adapt `data/` to the existing symlink. Do not pre-create empty
folders.

## Accepted (Unchanged)

| Element | Reason |
|---|---|
| `configs/{datasets,training,thresholding,analysis,suites}/` | Clean separation of scientific/runtime params; no hardcoded experiment logic |
| `src/datp_core/` domain-driven modules (`domain, config, utils, data, partitioning, models, federation, thresholding, experiments, evaluation, statistics, analyses, reporting`) | Matches the heavy/cheap reuse split; narrow interfaces |
| `tests/{unit,integration,fixtures}/` pyramid | Reviewer-proof separation of contract vs pipeline vs smoke |
| `checkpoints/` frozen weight vault (gitignored, read-only after selection) | Enforces fixed-encoder identity + reuse |
| `outputs/` complete runtime artifacts (gitignored) | Heavy/full artifacts kept out of `results/` |
| `results/` curated lightweight shareable derivations | Only citable/shareable derived artifacts |
| `scripts/{run_experiment,build_tables,build_figures,freeze_results}.py` | Thin entrypoints over the library; no logic |

## Changed

- **`data/raw`** is already a symlink to
  `/home/naslouby/Projects/datp-shared-data/raw`. Kept as-is; no committed
  `.gitkeep` trees inside a gitignored symlink target. `data/README.md`
  documents expected placement; presence/schema is verified at runtime by
  loaders + manifests, not by placeholder files.
- **`data/preprocessed/` and `outputs/*` subfolders** are created lazily by
  the ticket that owns them, not pre-seeded with `.gitkeep` sprawl.
- **`.env.example`** (when introduced in P1) documents only the data-root
  override and device env vars; canonical paths come from the path resolver
  (P1-T05), not env strings.
- **`personalized_ae.yaml`** naming never hardcodes `"Ditto"`; see
  [policies.md](policies.md).
- **`configs/thresholding/b_fedstats_benign.yaml`** locks the full
  pooled-variance + matched-exceedance contract before any computation.

## Rejected

| Element | Reason |
|---|---|
| `VERSIONING.md` | Versioning/release work is forbidden by `AGENTS.md`/`ai/`. |
| `CITATION.cff` | Release-package/citation metadata; out of scope now. |
| Pre-created empty `outputs/*/.gitkeep` for every experiment family | Premature folder sprawl; created lazily instead. |
| Any `compat/`, `legacy/`, `migrations/`, shim, or redirect module | No-backward-compatibility policy. |
| A separate wrapper module with no distinct behavior | Rejected as a behaviorless wrapper; anything carrying real read-only-load behavior distinct from save/select is kept as a normal module, not as a "compat" concept. |

## Preserved Governance Surfaces (Must Not Be Removed)

`AGENTS.md`, `ai/` (source of truth), `.claude/`, `.github/`, `.agents/`,
`.codex/`, `docs/`, `README.md`, `.gitignore`, the existing `data/raw`
symlink. These are inputs; tickets never rewrite them except where a ticket
explicitly owns a doc (e.g. `data/README.md`).

## Consumers

- `ai/skills/repo_structure_cleanliness_check.md` enforces this decision on
  every implementation ticket.
- P1-T01 (project skeleton) instantiates the accepted backbone.
