# CHECKLIST.md

## Preparation
- [x] Existing temporary state reviewed (none existed — fresh start)
- [x] Git working state recorded (clean, main, up to date with origin)
- [x] Active roadmap fully read (`docs/roadmap/` — 9 files, extraction in `ROADMAP_EXTRACTION.md`)
- [x] Drift audit A completed (`TARGET_ARCHITECTURE.md` top section)
- [x] Complete current tree documented (`CURRENT_ARCHITECTURE.md`)
- [x] Complete import graph documented (circular dep confirmed: `config/resolver.py ⇄ config/validation.py`; app↔infra cycle via `application/ports.py`)
- [x] Every source and test file added to migration map (`MIGRATION_MAP.md` — 88 production + 73 test files)
- [x] Final target tree approved by internal audit (`TARGET_ARCHITECTURE.md`)

## Production tree
- [ ] Configuration package migrated
- [ ] Experiments package migrated
- [ ] Dataset package migrated
- [ ] Learning package migrated
- [ ] Thresholding package migrated
- [ ] Evaluation package migrated
- [ ] Analysis package migrated
- [ ] Reporting package migrated
- [ ] Artifacts package migrated
- [ ] Pipeline package migrated
- [ ] Bootstrap migrated
- [ ] CLI migrated

## Old architecture removal
- [ ] Old `application/` deleted
- [ ] Old `composition/` deleted
- [ ] Old `config/` deleted
- [ ] Old `domain/` deleted
- [ ] Old `infrastructure/` deleted
- [ ] Old `interfaces/` deleted
- [ ] Old `planning/` deleted
- [ ] No old import path remains
- [ ] No redirect module remains
- [ ] No compatibility alias remains
- [ ] No duplicate moved implementation remains
- [ ] No empty obsolete package remains

## Architecture quality
- [ ] No circular dependency remains (resolver⇄validation cycle broken)
- [ ] No local import hides a cycle
- [ ] Feature ownership is clear
- [ ] Stage orchestration is thin
- [ ] No stage imports private helpers from another stage
- [ ] No miscellaneous support dumping ground remains (`stage_protocol.py`, `scoring_support.py`, `protocol_contracts.py`, `values.py` dissolved)
- [ ] No fake modularization remains
- [ ] No unnecessary micro-module remains
- [ ] No giant mixed-responsibility module remains
- [ ] Navigation audit passes for every capability
- [ ] Automated import-boundary rules exist (replacing `test_project_structure.py`/`test_application_port_dependency.py`)

## Typing and configuration
- [ ] No internal `dict[str, object]` remains (analysis_stages inter-method dicts, scoring_support returns, ThresholdSet.diagnostics)
- [ ] No internal `dict[str, Any]` remains
- [ ] No dynamic analysis-result contract remains (14 analysis kinds get typed results)
- [ ] No avoidable `Any` remains
- [ ] No avoidable broad `object` remains
- [ ] No unsafe cast remains
- [ ] No avoidable type ignore remains
- [ ] Closed vocabularies use authoritative enums
- [ ] Duplicate enums merged
- [ ] Duplicate records merged (`*MaterializationPayload` x3 → 1; seed-derivation x3 → 1)
- [ ] Configuration remains the source of truth
- [ ] No silent scientific default remains
- [ ] No unresolved hardcoded behavior value remains (flag `cv_instability_threshold` as pre-existing roadmap-flagged debt, not invented-away)

## Tests
- [ ] Test tree mirrors final feature architecture
- [ ] All production moves reflected in tests
- [ ] No old import path remains in tests
- [ ] No compatibility test remains
- [ ] No obsolete skipped test remains
- [ ] No obsolete xfailed test remains
- [ ] Dictionary fixtures replaced (`_statistical_analysis_fixtures.py`, `_synthetic_training_fixtures.py`)
- [ ] Duplicate fixtures removed
- [ ] Audit-only tests removed
- [ ] Test names clarified
- [ ] Stale comments and docstrings removed
- [ ] Every pipeline stage has direct tests
- [ ] Every analysis family has direct tests
- [ ] Every dataset adapter has direct tests
- [ ] Scientific invariants remain covered
- [ ] Dependency-boundary tests exist (new `tests/integration/test_dependency_boundaries.py`)

## Drift and pre-validation
- [ ] Drift audit B passed
- [ ] Source migration audit passed
- [ ] Old-tree deletion audit passed
- [ ] Navigation audit passed
- [ ] Implementation freeze recorded before validation

## Final validation
- [ ] Pyright passes with zero errors
- [ ] Pyright passes with zero warnings
- [ ] Pylance settings align with Pyright
- [ ] Direct Pylance diagnostics pass when available
- [ ] Complete test suite passes
- [ ] All pre-existing failures discovered were fixed
- [ ] Drift audit C passed
- [ ] No unresolved risk remains
- [ ] No commit was created
- [ ] No push was performed
