# Engineering case study draft — evidence-linked webhook investigation

**Status:** draft for owner review; no publication or user-adoption claim.

## Problem

Webhook incident exports often mix delivery attempts, processing steps, side effects and incomplete logs. A 2xx acknowledgement can be mistaken for completed work; a retry can be mistaken for a duplicate side effect. The tool helps an engineer inspect a bounded export and trace each finding back to records.

## Design

InvestigError defines a versioned JSON/JSONL contract with typed validation and generated schemas. A local CLI and loopback browser share the same parser, redactor, timeline and deterministic rules. R1 flags distinct committed effects under a declared single-effect invariant; R2 flags later application of a lower version under a declared monotonic invariant and explicit local sequence; R3 pairs acknowledgement and failure for one attempt. Findings carry evidence IDs, limitations and next checks. Synthetic .NET and Python exporters demonstrate that the contract is language-neutral.

An optional Anthropic call receives a selected, sanitized, bounded context only after explicit cloud permission. Structured output and cited IDs are checked. When the provider is unavailable or its response is invalid, the rules report remains available with an explicit status. The model suggests hypotheses and verification steps; deterministic rules establish the checkable observations.

## Measured verification in this repository

On 2026-09-25, the offline evaluation passed its quality gate on 18 synthetic bundles using exact finding/evidence labels. The local suite passed 91 tests; Ruff, mypy, schema freshness, the headless browser regression, .NET Release build and isolated installed-wheel smoke check also passed. These are software checks on fixtures, not production accuracy. CI runs lint, type checks, tests, schema freshness, sample validation, offline evaluation, .NET build and the installed-wheel smoke check.

## Unmeasured and pending

- **Live model accuracy/usefulness:** [unmeasured; requires configured model, authorized budget and human review].
- **Latency, token use and cost:** [unmeasured for live calls].
- **Production effectiveness or adoption:** [unmeasured; no real user or production incident study].
- **Security assurance for public hosting:** [not evaluated; local loopback use only].

The holdout cases were inspected during development, so fresh templates are needed before making a generalization claim. Redaction is best-effort and citations require human semantic review. Missing records and clock skew constrain causal conclusions. See [limitations](limitations.md).

## Draft technical article ideas

1. Designing an evidence contract that separates webhook delivery from committed effects.
2. Making provider failures visible while preserving deterministic findings.
3. Evaluating an LLM-assisted investigator without leaking labels into prompts.
