# Project status
Updated: 2026-10-04

## Current state
- INV-001 through INV-005 are merged into `main`; PR #5 merge `4d2b38b` was fetched and verified before this branch.
- Working functionality: versioned JSON/JSONL ingestion, deterministic evidence-linked findings, optional bounded Anthropic explanation in local mode, local browser UI, .NET and Python synthetic exporters, and an 18-case synthetic evaluation corpus.
- Known limitations: redaction is best-effort; missing records limit causal claims. Live model quality, latency, token use and cost remain unmeasured. The inspected synthetic holdout is regression coverage, not a production benchmark.

## Active task
- ID / outcome: INV-006 / Vercel-hosted rules demo.
- Status: in_progress; implementation and local checks complete, deployment awaiting Vercel account access.
- Branch / base revision: `feat/vercel-demo` / `4d2b38b` (`origin/main`).
- PR: [#6](https://github.com/razzv/InvestigError/pull/6), open for owner review.
- Scope: root Vercel FastAPI entrypoint, hosted UI disclosure, rules-only API guard, trusted hosts and HTTPS origin checks, deployment guide and regression test.

## Verification
- `uv run pytest -q`: 92 passed, including isolated Vercel-entrypoint request tests.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed.
- `uv run python scripts/generate_schemas.py --check`: passed.
- `npm run test:browser`: passed local preview, consent, rules, evidence, mocked AI, exports, upload, JSONL, error and mobile flow.
- Live Vercel function requests: not yet tested; Vercel CLI reports an invalid saved token and the browser requires sign-in.
- Live Anthropic calls: not tested; public mode blocks them.

## Next action
- Sign in to a Vercel account with access to `razzv/InvestigError`, connect or link the project, deploy a preview of this branch, and verify `/health`, an example rules report and the AI block on its URL.
- After owner review and merge, decide whether to promote the deployment to the production Vercel domain. Do not claim the hosted demo is live until the URL has been checked.
