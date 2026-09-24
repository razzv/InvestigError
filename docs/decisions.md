# Decisions

## 2026-09-24: Local Git bootstrap

The workspace had only a private build brief and no Git history or remote. The brief was moved to a sibling private directory before Git initialization. A single empty commit established local `main`; INV-001 was developed on `feat/incident-contract`. A PR requires an owner-designated remote.

After the owner published the feature branch, the new remote had no `main`. The existing empty bootstrap commit was pushed as `origin/main` to provide the intended PR base; the implementation remains only on the feature branch.
The remote default branch was set to `main` after PR #1 was opened, matching the repository workflow.

## 2026-09-24: Rule scope and conservative evidence

R1 uses the complete declared business tuple and distinct effect IDs. R2 requires a declared invariant and local sequence/version values. R3 matches service, provider, event and attempt; a provider must be equal on both records, including when both are absent. Repeated delivery and missing downstream records are informational observations. This prevents timestamps, retry logs and absence of capture from becoming unsupported fault claims.

## 2026-09-24: Offline report contract first

The output model includes explicit AI status and metadata fields so later provider work can extend the same report. INV-001 writes `not_requested` in rules mode; an AI request writes a rules report with `unavailable` and exits nonzero. No placeholder model answer is produced.

## 2026-09-24: Review fixes for bounded redaction and wire validation

Free-text redaction uses short `[E]` and `[S]` markers that do not expand a field already accepted by the input contract. Sensitive identifiers still receive stable collision-free aliases. Duplicate-ID errors report the record location without repeating the identifier, and validation text is passed through the known-pattern redactor before display. Wire timestamps require RFC 3339 strings with offsets; internal timezone-aware `datetime` values remain valid during sanitization. Numeric contract fields reject booleans and other coercible non-integers.
