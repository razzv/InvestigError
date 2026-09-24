# InvestigError

InvestigError reads structured webhook incident exports and creates an evidence-linked timeline and deterministic findings. Its rules mode runs locally without credentials or network access. An optional Anthropic explanation call can add hypotheses and next checks when the user explicitly enables cloud transmission.

This is an investigation aid. A finding describes the supplied records and declared invariants; missing logs do not prove an operation never happened.

## Try it

Install [uv](https://docs.astral.sh/uv/), then run from the repository root:

```sh
uv sync --extra dev
uv run investigerror validate examples/incidents/example-001.json
uv run investigerror analyze examples/incidents/example-001.json --mode rules --out artifacts/report.json
```

The analysis writes `artifacts/report.json` and `artifacts/report.md`. Use `--overwrite` to replace either file. Try `example-002` through `example-005` for duplicate effects, stale state, a complete trace and missing downstream evidence. See [the format guide](docs/incident-format.md) and [development guide](docs/development.md).

For an AI explanation, set `ANTHROPIC_API_KEY` and `AI_MODEL` in your shell, then run:

```sh
uv run investigerror analyze examples/incidents/example-001.json --mode ai --allow-cloud --out artifacts/ai-report.json
```

`--allow-cloud` sends selected, sanitized incident records and deterministic findings to Anthropic. Inspect the input first and review the report before sharing it. No model is selected by default. A missing key/model or a provider or validation failure leaves the rules report in place and exits nonzero. The model's statements remain hypotheses; evidence references are checked for existence, not automatically verified for semantic support. No live provider call has been verified for this task.

The package and CLI are named `investigerror`. JSON and JSONL are supported. Python 3.13.2 was used for local verification; the declared minimum is Python 3.12.

## Local browser UI

```sh
uv run investigerror serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Load a bundled example or upload JSON/JSONL, validate to inspect the sanitized input and exact selected provider context, then run rules. Evidence links select the corresponding record. JSON and Markdown downloads are created in the browser; the server does not save uploads or reports. The API accepts bounded raw file bytes in memory and rejects streams over 2 MiB. AI requires a separate unchecked cloud confirmation after preview. Missing credentials leave the rules report available with `unavailable` status. Redaction is best-effort; inspect the selected context before authorizing transmission. The local service is limited to loopback and is not designed for public hosting.

## Current scope

INV-001 supplies the versioned contract, bounded ingestion, redaction, correlation, rules, synthetic examples, CLI and JSON/Markdown exports. INV-002 adds one bounded, structured provider call, validation and a synthetic prompt-injection fixture. INV-003 adds the local browser UI and API. INV-004 adds [.NET and Python exporters](docs/cross-language.md) and an [18-case synthetic evaluation](docs/evaluation.md). Run `uv run investigerror evaluate --mode rules --split all --out artifacts/evaluation.json` for the offline report. Passing synthetic cases does not measure live model quality or production accuracy. Redaction is best-effort; review reports before sharing them.
