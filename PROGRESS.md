# Project status
Updated: 2026-09-24

## Current state
- Working functionality: offline JSON/JSONL investigation and optional, explicitly authorized Anthropic explanation with bounded sanitized context, schema/evidence validation and rules-report fallback.
- Known limitations: live model quality and behavior are unmeasured because no key/model is configured. Browser UI and cross-language exporter are later tasks. Redaction is best-effort.

## Active task
- ID / outcome: INV-002 / bounded provider explanation and evidence validation.
- Status: ready_for_review
- Branch / base revision: `feat/provider-evidence` / `9c48276` (`origin/main`, verified merge of [INV-001 PR #1](https://github.com/razzv/InvestigError/pull/1)).
- PR: pending creation.
- Dependencies: INV-001 merged.

## Verification
- Revision checked: INV-002 working tree before task commit, based on INV-001 merge `9c48276`.
- Commands and observed outcomes: `uv sync --locked --extra dev` succeeded; `uv run pytest -q` passed 66 tests; `uv run ruff check .` and `uv run mypy src` passed; `uv run pytest -q tests/test_schemas.py` passed. Built a wheel and verified its prompt and CLI from an installed environment outside the repository. Missing-key AI CLI exited 3 and wrote an `unavailable` report retaining R3. Python 3.13.2; Anthropic SDK 1.8.0.
- Checks not run and why: no live model call; `ANTHROPIC_API_KEY` and `AI_MODEL` are not configured. Semantic quality is unmeasured. .NET is not part of INV-002.

## Next action
- Push this branch and open the INV-002 PR into `main`; wait for owner merge before INV-003.
- Open blocker or owner decision: none for PR creation.
