# outputs/

Gitignored. Holds complete runtime artifacts: logs, per-client/per-seed
scores, threshold artifacts, prediction artifacts, metrics, statistics
summaries, raw tables, raw figures, and run manifests, keyed by experiment id
(see [docs/protocol/naming_conventions.md](../docs/protocol/naming_conventions.md)).

`outputs/` is the full, heavy, reproducible-but-not-curated artifact store.
Only the subset that is citable/shareable is promoted to `results/` by result
curation (P7-T06). See
[docs/protocol/artifact_contracts.md](../docs/protocol/artifact_contracts.md)
for the artifact-to-stage mapping.

Subdirectories are created lazily by the ticket that first produces that
artifact class; none are pre-seeded.
