# Project status
Updated: 2026-09-24

## Current state
- Working functionality: offline JSON/JSONL validation, sanitized timeline, deterministic R1-R3 findings and evidence-linked JSON/Markdown CLI reports.
- Known limitations: no provider adapter, HTTP API, browser UI or cross-language exporter yet. Redaction is best-effort.

## Active task
- ID / outcome: INV-001 / incident contract, core rules and CLI.
- Status: ready_for_review
- Branch / base revision: `feat/incident-contract` / `0c697f2` (empty `main` bootstrap, now published to `origin`).
- PR: pending creation against `origin/main`.
- Dependencies: none.

## Verification
- Revision checked: working tree before task commit.
- Commands and observed outcomes: `uv sync --extra dev` succeeded with Python 3.13.2; `uv run pytest -q` passed 23 tests; `uv run ruff check .` and `uv run mypy src` passed; schema freshness test passed; JSON and JSONL validation passed; rules analysis wrote JSON/Markdown; the installed CLI validated a bundle from another working directory.
- Checks not run and why: no live AI or .NET execution is part of INV-001.

## Next action
- Push this branch and open the INV-001 PR into `main`; wait for the owner merge before INV-002.
- Open blocker or owner decision: none for PR creation.
