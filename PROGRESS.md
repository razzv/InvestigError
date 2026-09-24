# Project status
Updated: 2026-09-25

## Current state
- Working functionality: versioned JSON/JSONL ingestion, deterministic evidence-linked findings, optional bounded Anthropic explanation, loopback browser UI, .NET and Python synthetic exporters, and an 18-case synthetic evaluation corpus.
- Known limitations: redaction is best-effort; missing records limit causal claims. Live model quality, latency, token use and cost remain unmeasured. The inspected synthetic holdout is regression coverage, not a production benchmark. See [limitations](docs/limitations.md).

## Active task
- ID / outcome: INV-005 / delivery documentation, learning walkthrough, CI packaging check and case-study draft.
- Status: ready_for_review.
- Branch / base revision: `docs/inv-005-delivery` / `380ba7d` (`origin/main`, verified merge of [INV-004 PR #4](https://github.com/razzv/InvestigError/pull/4)).
- PR: [#5](https://github.com/razzv/InvestigError/pull/5), open for owner review.
- Dependencies: INV-004 merged.

## Verification
- Revision checked: INV-005 review corrections on `docs/inv-005-delivery`, based on `86c0438`.
- Completed corrections: the demo now reads quality-gate status and per-class rule metrics from `artifacts/evaluation.json`, and the human review sheet and unreviewed live-model fields from `artifacts/evaluation.md`. The timeout exercise now describes `ProviderFailure` as `ai_status: failed`, with rules findings preserved and a nonzero CLI exit. PR URL recorded above.
- Commands and observed outcomes: `uv run pytest -q tests/test_explanation.py -k provider_failure_keeps_rules_report_without_retry` passed (2 parametrized cases); the regression asserts `failed` and preserved R3 findings. CLI exit code 3 for unsuccessful AI requests was confirmed in `src/investigerror/cli.py`. Generated artifacts show 18 cases, `measured_offline`, a passed quality gate, and R1/R2/R3 precision and recall of 1.0 on this synthetic corpus; the Markdown sheet marks live-model review fields `unreviewed`. Prior full INV-005 checks passed locally: 91 tests, Ruff, mypy, schema freshness, sample validation, 18-case offline quality gate, browser flow, .NET Release build and sample checks, and installed-wheel smoke check. Both GitHub Actions checks on PR #5 passed.
- Checks not run and why: no full-suite rerun for these documentation-only corrections. No live Anthropic call because credentials and an authorized evaluation budget are not configured. macOS/Linux setup was not run natively; CI runs Linux/Python 3.12 checks.

## Next action
- Wait for owner review and merge of PR #5. Do not start another task, deploy or publish a release.
- Open blocker or owner decision: none.
