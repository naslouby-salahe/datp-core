# Manuscript Workflow

## Use when
Use for paper, README prose, LaTeX, Markdown, captions, abstract, introduction, related work, discussion, conclusion, and reviewer-facing text.

## Required gates
`contract_gate`, `claim_evidence_hook`, `manuscript_integrity_check`, `literature_overlap_check`, `comment_hook`, `reviewer_attack_check`, `cleanup_hook`, `final_report_hook`.

## Completion requirements
Claim-evidence and manuscript-integrity checks pass. Hype, unsupported first claims, unsupported privacy claims, unsupported deployment claims, unsupported robustness claims, unsupported causal language, stale wording, and AI-looking filler are absent.

## Final report requirements
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include changed files, claim classifications, evidence used, wording constraints, checks run, cleanup, skipped checks, and remaining reviewer risks.
