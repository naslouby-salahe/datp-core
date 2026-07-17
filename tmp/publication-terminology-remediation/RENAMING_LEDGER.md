# Renaming Ledger

| Old Name | New Name | Reason | Classification |
|---|---|---|---|
| `ProtocolTrack.JOURNAL_EXTENSION` | `ProtocolTrack.COMPLETE` | Names protocol track by study scope, not publication destination | D |
| `ProtocolTrack.JOURNAL_EXTENSION` value `"journal_extension"` | `"complete"` | Serialized value must match enum rename | D |
| `ArtifactNamespace.JOURNAL_EXTENSION` | `ArtifactNamespace.COMPLETE` | Names artifact namespace by study scope | D |
| `ArtifactNamespace.JOURNAL_EXTENSION` value `"journal_extension"` | `"complete"` | Serialized value must match enum rename | D |
| `CheckpointProtocol.JOURNAL_SCHEDULED` | `CheckpointProtocol.COMPLETE_SCHEDULED` | Names checkpoint protocol by its role in complete study schedule | D |
| `CheckpointProtocol.JOURNAL_SCHEDULED` value `"journal_scheduled"` | `"complete_scheduled"` | Serialized value must match enum rename | D |
| `LifecycleJournalEntry` | `LifecycleLogEntry` | "Journal" means "append-only log"; removes publication ambiguity | D |
| `journal_path` (local variable) | `lifecycle_log_path` | Describes what the path is, not publication lifecycle | D |
| `journal` (file handle) | `log_file` | Describes what the handle is | D |
| `require_journal_expansion` | `require_anchor_passage` | Names gate method by what it checks (anchor passage), not publication | D |
| `journal_extension` (YAML config values) | `complete` | Config values match enum rename | D |
| `journal_fedavg` (YAML config values) | `complete_fedavg` | Model profile ID matches enum rename | D |
| `outputs/journal/` directory | `outputs/complete/` | Output directory matches namespace rename | D |

### Kept (not renamed)

| Symbol | Reason |
|---|---|
| `ManuscriptPlacement` (MAIN, SUPPLEMENT) | Legitimate reporting terminology — where a result appears in the manuscript |
| All `manuscript_*` agent/contract/workflow/skill files | Legitimate manuscript-editing/prose concerns |
| `Journal_Extension_Master_Roadmap.md` | Document identity/name |
| `DATP Journal Extension` in titles | Project identity |
| All `conference` references in roadmap | Legitimate venue comparison for originality |
| All `paper` references in provenance | Legitimate reference to conference paper |
| `camera-ready` timing references | Legitimate cover-letter requirement |
| `venue` declarations | Legitimate publication venue specification |
| `publication` in duplicate-publication ethics | Legitimate ethical concern |
| All `anchor` concepts | Preserved per prompt rules |
| All B0-B4 identifiers | Scientific comparator identities |
| All regime names (A, B-a, C, D, D-temporal) | Scientific experiment identities |

