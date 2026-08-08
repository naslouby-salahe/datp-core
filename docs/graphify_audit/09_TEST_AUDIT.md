# Test audit

`pytest --collect-only` found 819 tests; full `pytest -q` passed **819/819** (192 PyTorch pin-memory deprecation warnings). Ruff and Pyright reported zero findings.

- No production module imports tests or a test library: no production→test dependency exists.
- DC-04/05 are the confirmed test-only production helpers; migrate their tests to canonical capability/protocol validation before deletion.
- Existing historical external-artifact parsing intentionally ignores a legacy token. It is a safe anchor-isolation boundary, not a compatibility API to remove.
- CUDA-specific tests are intentionally skipped without CUDA. Keep a CUDA CI/release lane as evidence; a CPU green suite cannot prove device-specific determinism/score behavior.
- Add integration coverage for WL-01/05/07, II-01–04, and the stale split guard AD-03. Add regression tests for deleted APIs only by asserting canonical paths, never a shim.

