# data/

`data/raw` is a symlink to `/home/naslouby/Projects/datp-shared-data/raw` and
is gitignored. Do not move or modify raw datasets. Do not commit placeholder
trees inside the symlink target.

Expected layout under `data/raw/`: `nbaiot/`, `ciciot2023/`, `edge_iiotset/`.
Presence and schema are verified at runtime by dataset loaders (P2, P6), not
by this README. See [docs/protocol/artifact_contracts.md](../docs/protocol/artifact_contracts.md)
for the full per-dataset contract.

`data/preprocessed/` and `data/manifests/` are created lazily by the ticket
that owns them (P1-T07, P1-T08, P2-T02) and are gitignored.
