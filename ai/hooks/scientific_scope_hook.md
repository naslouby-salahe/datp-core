# Scientific Scope Hook

## Trigger
After any edit touching protocol, experiments, results, claims, or repository governance.

## Purpose
Block drift outside the locked DATP journal-extension identity.

## Blocking status
Blocks completion.

## Required checks
- The fixed encoder, FedAvg baseline (E=1, full participation), and threshold-calibration scope as the sole causal-ladder variable are preserved.
- Calibration remains benign-only; attack data is never used to fit or tune a threshold.
- AUROC remains a model-quality control metric, never the primary thresholding verdict; the primary operating-point concern remains per-client FPR disparity, not global F1/AUROC/accuracy.
- Stress-test comparators (FedProx, model personalization, Laridi-style) stay outside the causal threshold-scope ladder and are never presented as sharing its experimental control.
- No drift into Dynamic DATP, poisoning, privacy guarantees, deployment profiling, backdoor, evasion, full drift detection, or generic FL-IDS expansion; any such mention is explicitly future-work or spin-off wording, never an executable path.
- No supportive, exploratory, or stress-test evidence is promoted to confirmatory status.

## Failure behavior
Stop the edit and report the exact scope violation; never silently narrow or reinterpret the locked identity to make an edit fit.
