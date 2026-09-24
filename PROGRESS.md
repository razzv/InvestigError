# Project status
Updated: 2026-09-24

## Current state
- Working functionality: versioned JSON/JSONL ingestion, deterministic investigation, optional bounded Anthropic explanation, loopback browser UI, .NET and Python synthetic exporters, and a split 18-case evaluation corpus.
- Known limitations: redaction is best-effort. Live model quality and behavior remain unmeasured without configured credentials/model and an authorized evaluation budget. Synthetic scores do not establish production accuracy.

## Active task
- ID / outcome: INV-004 / cross-language sample and synthetic evaluation review fixes.
- Status: ready_for_review.
- Branch / base revision: `feat/dotnet-python-evaluation` / `09f573e` (`origin/main`, verified merge of [INV-003 PR #3](https://github.com/razzv/InvestigError/pull/3)).
- PR: [#4](https://github.com/razzv/InvestigError/pull/4), open for review.
- Dependencies: INV-003 merged.

## Verification
- Revision checked: INV-004 review-fix working tree on PR #4, based on `09f573e`.
- Commands and observed outcomes: `uv run pytest -q` passed 91 tests, including mocked interrupted provider runs, multi-finding grading, non-ASCII outbound context bounds, and all four .NET/Python export modes. Ruff, mypy, schema generation/freshness, sample validation, 18-case offline evaluation, mocked browser flow and .NET Release build passed. The offline quality gate passed; this is synthetic software correctness, not a live model benchmark.
- Checks not run and why: no live Anthropic call because credentials/model and an authorized evaluation budget are not configured. Model quality remains unmeasured.

## Next action
- Wait for owner review and merge of PR #4. Do not start INV-005.
- Open blocker or owner decision: none.
