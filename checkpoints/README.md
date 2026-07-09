# checkpoints/

Gitignored. Holds frozen FedAvg autoencoder weights, one per
(dataset, regime, seed, α). A checkpoint is read-only once frozen (P2-T07):
no ticket retrains or overwrites an existing frozen checkpoint in place.

Reuse-validity key: dataset + regime + seed + α (see
[docs/protocol/artifact_contracts.md](../docs/protocol/artifact_contracts.md)).
B1–B4 for a given (dataset, regime, seed, α) all read the same frozen
checkpoint; no threshold-only ticket triggers retraining
([docs/protocol/reuse_policy.md](../docs/protocol/reuse_policy.md)).

Subdirectories are created lazily by the tickets that own them (P2-T07,
P6-T05, P6-T10, P6-T11).
