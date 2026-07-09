# Claim Evidence Hook

## Trigger
After docs, manuscript, result summaries, captions, diagrams, or reviewer-response edits.

## Purpose
Ensure claims are evidence-backed and correctly classified.

## Blocking status
Blocks completion.

## Required checks
- Every claim maps to evidence.
- Claim classification is explicit when needed.
- No claim inflation, unsupported causal wording, or unsupported generalization.

## Failure behavior
Remove, soften, or classify the claim; stop if evidence is unavailable.
