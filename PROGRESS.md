# Project status
Updated: 2026-09-24

## Current state
- Working functionality: versioned JSON/JSONL investigation, offline rules and exports, optional bounded Anthropic explanation, and a loopback FastAPI/static browser workflow with examples, sanitized preview, evidence links and downloads.
- Known limitations: redaction is best-effort; live model quality and behavior remain unmeasured without configured credentials/model. Cross-language exporters and evaluation are later tasks.

## Active task
- ID / outcome: INV-003 / local API and browser UI.
- Status: ready_for_review
- Branch / base revision: `feat/local-browser-ui` / `c55ceb3` (`origin/main`, verified merge of [INV-002 PR #2](https://github.com/razzv/InvestigError/pull/2)).
- PR: [#3](https://github.com/razzv/InvestigError/pull/3), open for review.
- Dependencies: INV-002 merged.

## Verification
- Revision checked: INV-003 review-fix working tree on PR #3, based on `c55ceb3`.
- Commands and observed outcomes: `uv sync --locked --extra dev` passed; `uv run pytest -q` passed 75 tests; `uv run ruff check .`, `uv run mypy src`, JavaScript syntax, and schema generation/freshness passed. `npm ci` and `npm run test:browser` passed a headless Chrome flow covering upload, validation, consent, rules, evidence navigation, mocked successful AI output, exports, JSONL, errors and mobile layout. Direct ASGI streaming and controlled provider concurrency regressions passed. `uv build --wheel` passed and the reinstalled wheel served the raw API and UI assets outside the repository on Python 3.13.2; review also verified the desktop UI interactively.
- Checks not run and why: no live Anthropic call because key/model are not configured. .NET is outside INV-003.

## Next action
- Wait for owner review and merge of PR #3 before INV-004.
- Open blocker or owner decision: none for PR creation.
