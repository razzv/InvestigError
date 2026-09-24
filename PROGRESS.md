# Project status
Updated: 2026-09-24

## Current state
- Working functionality: versioned JSON/JSONL ingestion, deterministic investigation, optional bounded Anthropic explanation, loopback browser UI, .NET and Python synthetic exporters, and a split 17-case evaluation corpus.
- Known limitations: redaction is best-effort. Live model quality and behavior remain unmeasured without configured credentials/model and an authorized evaluation budget. Synthetic scores do not establish production accuracy.

## Active task
- ID / outcome: INV-004 / cross-language sample and synthetic evaluation.
- Status: ready_for_review.
- Branch / base revision: `feat/dotnet-python-evaluation` / `09f573e` (`origin/main`, verified merge of [INV-003 PR #3](https://github.com/razzv/InvestigError/pull/3)).
- PR: pending.
- Dependencies: INV-003 merged.

## Verification
- Revision checked: INV-004 working tree based on `09f573e`.
- Commands and observed outcomes: `uv run pytest -q` passed 85 tests including all four .NET/Python export modes; Ruff, mypy, schema freshness, sample validation, offline evaluation and .NET Release build passed. The 17-case offline quality gate passed; per-class counts are in the generated report, not a live model benchmark.
- Checks not run and why: no live Anthropic call because credentials/model and an authorized evaluation budget are not configured. Model quality remains unmeasured.

## Next action
- Open INV-004 PR into main, then wait for owner review and merge. Do not start INV-005.
- Open blocker or owner decision: none for PR creation.
