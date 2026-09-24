# InvestigError

InvestigError reads structured webhook incident exports and creates an evidence-linked timeline and deterministic findings. Its rules mode runs locally without credentials or network access. An optional LLM explanation is planned for INV-002; this version does not call a model.

This is an investigation aid. A finding describes the supplied records and declared invariants; missing logs do not prove an operation never happened.

## Try it

Install [uv](https://docs.astral.sh/uv/), then run from the repository root:

```sh
uv sync --extra dev
uv run investigerror validate examples/incidents/example-001.json
uv run investigerror analyze examples/incidents/example-001.json --mode rules --out artifacts/report.json
```

The analysis writes `artifacts/report.json` and `artifacts/report.md`. Use `--overwrite` to replace either file. Try `example-002` through `example-005` for duplicate effects, stale state, a complete trace and missing downstream evidence. See [the format guide](docs/incident-format.md) and [development guide](docs/development.md).

The package and CLI are named `investigerror`. JSON and JSONL are supported. Python 3.13.2 was used for local verification; the declared minimum is Python 3.12.

## Current scope

INV-001 supplies the versioned contract, bounded ingestion, redaction, correlation, rules, five synthetic examples, CLI and JSON/Markdown exports. The browser UI, LLM provider, evaluation corpus and cross-language examples are later tasks in [the backlog](docs/backlog.md). Redaction is best-effort; review reports before sharing them.
