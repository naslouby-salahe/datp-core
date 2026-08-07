# 08 — Primitive Leaks

Audit of inappropriate domain/scientific leakage through raw types.

---

## CLEAN: No `Any` Types

Single occurrence of `Any` in production code is in a comment (`planning.py:160`). Zero actual `Any` type annotations.

## CLEAN: No `dict[str, Any]` or `object` as Domain Contract

All domain boundaries use typed models (StrictModel, frozen dataclasses, enums). Dictionaries isolated to library boundaries (polars DataFrames, JSON serialization).

## CLEAN: No `# type: ignore` in Production

Zero type-ignore suppressions in `src/`. All suppressions are in test files only.

---

## VALUE OBJECT COVERAGE

Strong primitive wrapping through value objects:

| Primitive | Wrapped As | File |
|-----------|-----------|------|
| `int` (seed) | `Seed` | domain/values/counts.py |
| `int` (count) | `RowCount`, `ClientCount`, `RoundNumber`, `BatchSize`, `FeatureCount` | domain/values/counts.py |
| `int` (bytes) | `ByteCount` | domain/values/counts.py |
| `str` (checksum) | `Checksum` | domain/values/checksums.py |
| `float` (quantile) | `Quantile` | domain/values/ratios.py |
| `float` (metric) | `MetricValue` | domain/values/ratios.py |
| `float` (confidence) | `ConfidenceLevel` | domain/values/ratios.py |
| `float` (concentration) | `DirichletConcentration` | domain/values/ratios.py |
| `float` (coefficient) | `ModelCoefficientValue` | domain/values/ratios.py |
| `float` (learning rate) | `LearningRate` | domain/values/ratios.py |
| `float` (weight decay) | `WeightDecay` | domain/values/ratios.py |
| `tuple[str,...]` (features) | `FeatureNameSequence` | domain/values/identifiers.py |
| `str` (timestamp col) | `CaptureTimestampColumn` | domain/values/identifiers.py |
| `str` (device) | `CudaDeviceName` | domain/values/identifiers.py |
| `str` (client path) | `ClientPathToken` | domain/values/paths.py |

## ENUM COVERAGE

All closed categorical domains use enums:

- DatasetId, PopulationId, ExperimentId, EvidenceRole, FederatedThresholdMethod, MetricId, etc.
- No raw string comparisons for domain concepts
- Serialized values converted to enums at boundaries

---

## MINOR LEAKS

### PL-001: Output Path Construction Uses Raw `str`

- **File:** Multiple locations in `pipeline/execution/layout.py`, `pipeline/publication/layout.py`
- **Problem:** Output directory paths are constructed with f-strings and `/` operators using `str(value)` or `.value`. These are typed value objects, so this is acceptable — the value object wrapping serves the domain layer. Path construction is a presentation concern.
- **Severity:** NOT A LEAK — acceptable boundary between domain values and filesystem

### PL-002: `Path` Used Directly (Not Wrapped)

- **File:** Throughout codebase
- **Problem:** `pathlib.Path` used directly for filesystem operations. No `OutputPath` or `ArtifactPath` wrapper exists.
- **Assessment:** `Path` is a standard library type with rich semantics. Wrapping it would add indirection without preventing errors. Acceptable.
- **Severity:** NOT A LEAK

---

## Summary

| Category | Status |
|----------|--------|
| `Any` types | CLEAN (0 instances) |
| `dict[str, Any]` | CLEAN (0 instances) |
| `# type: ignore` in src | CLEAN (0 instances) |
| Value object coverage | STRONG (15+ wrappers) |
| Enum coverage | STRONG (30+ enums) |
| Raw string domain comparisons | CLEAN (0 instances) |
| Primitive leaks requiring fix | NONE |

**No primitive leaks identified.** The codebase has excellent type discipline.
