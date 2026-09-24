# Project status
Updated: 2026-09-25

## Current state
- Working functionality: versioned JSON/JSONL ingestion, deterministic evidence-linked findings, optional bounded Anthropic explanation, loopback browser UI, .NET and Python synthetic exporters, and an 18-case synthetic evaluation corpus.
- Known limitations: redaction is best-effort; missing records limit causal claims. Live model quality, latency, token use and cost remain unmeasured. The inspected synthetic holdout is regression coverage, not a production benchmark. See [limitations](docs/limitations.md).

## Active task
- ID / outcome: INV-005 / delivery documentation, learning walkthrough, CI packaging check and case-study draft.
- Status: ready_for_review.
- Branch / base revision: `docs/inv-005-delivery` / `380ba7d` (`origin/main`, verified merge of [INV-004 PR #4](https://github.com/razzv/InvestigError/pull/4)).
- PR: pending creation.
- Dependencies: INV-004 merged.

## Verification
- Revision checked: INV-005 working tree before commit.
- Commands and observed outcomes: `uv sync --locked --extra dev`; `uv run pytest -q` (91 passed); `uv run ruff check .`; `uv run mypy src`; schema generation and `git diff --exit-code -- schemas/ evaluation/`; sample validation and rules analysis; 18-case offline evaluation (quality gate passed); `npm ci` and `npm run test:browser`; .NET Release build, `check fixed` and fixed export; `uv build` and `uv run python scripts/check_installed_package.py` (wheel installed in a fresh temporary environment and CLI/resources checked outside the repository) all passed locally. The documented relative .NET export path initially failed; the demo script now uses an absolute path, which passed.
- Checks not run and why: no live Anthropic call because model credentials and an authorized evaluation budget are not configured. No macOS/Linux machine was available for native setup verification; CI uses Linux/Python 3.12 for package and offline checks.

## Next action
- Open the INV-005 PR into `main` after final diff review; owner reviews and merges. Do not deploy or publish a release.
- Open blocker or owner decision: none.
