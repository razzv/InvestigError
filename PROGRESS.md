# Project status
Updated: 2026-09-24

## Current state
- Working functionality: versioned JSON/JSONL investigation, offline rules and exports, optional bounded Anthropic explanation, and a loopback FastAPI/static browser workflow with examples, sanitized preview, evidence links and downloads.
- Known limitations: redaction is best-effort; live model quality and behavior remain unmeasured without configured credentials/model. Browser visual interaction could not be verified because the computer-use service exposed no browser surfaces. Cross-language exporters and evaluation are later tasks.

## Active task
- ID / outcome: INV-003 / local API and browser UI.
- Status: ready_for_review
- Branch / base revision: `feat/local-browser-ui` / `c55ceb3` (`origin/main`, verified merge of [INV-002 PR #2](https://github.com/razzv/InvestigError/pull/2)).
- PR: pending creation.
- Dependencies: INV-002 merged.

## Verification
- Revision checked: INV-003 working tree before task commit, based on INV-002 merge `c55ceb3`.
- Commands and observed outcomes: `uv sync --locked --extra dev` passed; `uv run pytest -q` passed 73 tests; `uv run ruff check .`, `uv run mypy src`, `node --check src/investigerror/static/app.js`, and schema generation/freshness passed. `uv build --wheel` passed; installed wheel served UI and examples from a separate working directory on Python 3.13.2. Local Uvicorn started at `127.0.0.1:8000`.
- Checks not run and why: browser visual interaction was unavailable (`cua` reported no browser surfaces); no live Anthropic call because key/model are not configured. .NET is outside INV-003.

## Next action
- Push this branch and open the INV-003 PR into `main`; wait for owner merge before INV-004.
- Open blocker or owner decision: none for PR creation.
