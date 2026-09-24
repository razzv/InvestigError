# Project status
Updated: 2026-09-24

## Current state
- Working functionality: offline JSON/JSONL validation, sanitized timeline, deterministic R1-R3 findings and evidence-linked JSON/Markdown CLI reports. PR review fixes cover bounded redaction, safe duplicate-ID errors and strict timestamp/integer wire values.
- Known limitations: no provider adapter, HTTP API, browser UI or cross-language exporter yet. Redaction is best-effort.

## Active task
- ID / outcome: INV-001 / incident contract, core rules and CLI.
- Status: ready_for_review
- Branch / base revision: `feat/incident-contract` / `0c697f2` (empty `main` bootstrap, now published to `origin`).
- PR: [#1](https://github.com/razzv/InvestigError/pull/1), open and ready for owner review against `main`.
- Dependencies: none.

## Verification
- Revision checked: working tree before review-fix commit.
- Commands and observed outcomes: `uv run pytest -q` passed 43 tests; `uv run ruff check .` passed; `uv run mypy src` passed for nine source files; `uv run pytest -q tests/test_schemas.py` passed. Schema regeneration produced no diff. Earlier `uv sync --extra dev` and CLI smoke tests passed with Python 3.13.2.
- Checks not run and why: no live AI or .NET execution is part of INV-001.

## Next action
- Wait for the owner to merge PR #1, then fetch `main` and begin INV-002 from the merged revision.
- Open blocker or owner decision: owner merge of PR #1.
