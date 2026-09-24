# Development

Use Python 3.12 or newer, [uv](https://docs.astral.sh/uv/) and Git. Clone the repository, enter its root, and run the commands below. The lock file controls Python dependencies. .NET SDK 9 is needed for the cross-language sample and its full test coverage; Node.js and npm are needed for the browser regression.

Windows PowerShell:

```powershell
git clone https://github.com/razzv/InvestigError.git
Set-Location InvestigError
uv sync --locked --extra dev
uv run investigerror validate examples/incidents/example-001.json
uv run investigerror analyze examples/incidents/example-001.json --mode rules --out artifacts/report.json
uv run investigerror serve --host 127.0.0.1 --port 8000
```

macOS/Linux shell:

```sh
git clone https://github.com/razzv/InvestigError.git
cd InvestigError
uv sync --locked --extra dev
uv run investigerror validate examples/incidents/example-001.json
uv run investigerror analyze examples/incidents/example-001.json --mode rules --out artifacts/report.json
uv run investigerror serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` after the server starts; stop it with Ctrl+C. For another example or repeat run, choose a new output path or pass `--overwrite`. The [demo script](demo-script.md) shows a short walkthrough. The [architecture diagram](architecture.md) and [limitations](limitations.md) explain what the report can support.

Required offline checks from the repository root:

```sh
uv sync --locked --extra dev
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python scripts/generate_schemas.py
uv run investigerror validate examples/incidents/example-001.json
uv run investigerror analyze examples/incidents/example-001.json --mode rules --out artifacts/check-report.json --overwrite
uv run investigerror evaluate --mode rules --split all --out artifacts/evaluation.json
dotnet build examples/dotnet/InvestigError.Sample/InvestigError.Sample.csproj --configuration Release
uv build
uv run python scripts/check_installed_package.py
```

After schema generation, `git diff --exit-code -- schemas/` verifies that committed schemas are current. After the offline evaluation, `git diff --exit-code -- evaluation/` verifies that the corpus was not changed. The installed-wheel smoke check is `uv run python scripts/check_installed_package.py` after `uv build`; it creates a temporary clean environment, installs the wheel and invokes the CLI from another directory.

For the mocked browser regression, run `npm ci` and `npm run test:browser` after `uv sync --locked --extra dev`. It starts a temporary loopback server with synthetic provider output and runs headless Chrome through Playwright. Set `INV_BROWSER_CHANNEL` to another installed Chromium channel if Chrome is unavailable. No provider credentials or live call are used.

The cross-language sample needs .NET SDK 9. See [cross-language commands](cross-language.md) and the [evaluation protocol](evaluation.md). The test suite compares the .NET and Python exporters when the SDK is available. CI installs the SDK and runs that comparison, schema freshness and offline evaluation; it does not call a live model.

AI is optional. Set `ANTHROPIC_API_KEY` and an explicit `AI_MODEL` in the shell; `.env.example` documents the names but is not loaded automatically. `AI_TIMEOUT_SECONDS` defaults to 30 and `AI_MAX_OUTPUT_TOKENS` to 3000. For example, in PowerShell use `$env:ANTHROPIC_API_KEY = '...'` and `$env:AI_MODEL = '...'`; in macOS/Linux shells use `export ANTHROPIC_API_KEY=...` and `export AI_MODEL=...`. Then run `uv run investigerror analyze examples/incidents/example-001.json --mode ai --allow-cloud --out artifacts/ai-report.json`. The explicit flag authorizes transmission of the selected sanitized context to Anthropic. The application does not choose a model or make a call without it.

Run from another working directory with the installed command in `.venv/Scripts/investigerror.exe` on Windows or `.venv/bin/investigerror` on macOS/Linux. Outputs belong under gitignored `artifacts/`; use `--overwrite` to replace them. `validate` exits 2 on invalid input. `analyze` exits 2 on invalid input or an existing output, and exits 3 for a requested AI explanation that could not run after writing the rules report. A successful report exits 0 even if it contains a fault finding.

Core flow: `ingestion.py` parses and validates; `redaction.py` masks known secrets; `correlation.py` builds the timeline; `rules.py` makes checkable findings; `analysis.py` assembles the rules report. For AI mode, `context.py` selects complete finding evidence within 100 records and 40,000 serialized characters; `explanation.py` validates the structured response and references; `providers/anthropic.py` performs one SDK request with an explicit timeout and at most one SDK retry. `reporting.py` renders safe Markdown; `cli.py` provides commands. The JSON Schemas in `schemas/` are generated from `models.py`. The versioned prompt is packaged under `src/investigerror/prompts/`.

`api.py` serves static assets and packaged examples. `POST /api/validate`, `/api/analyze`, and `/api/explain` accept raw JSON or JSONL bytes with `X-Incident-Format: json` or `jsonl`. The request stream is capped at 2 MiB before parsing; accepted data is buffered only in bounded memory, without multipart disk spooling. Validation returns sanitized input, input limitations and the exact bounded provider context; an oversized context returns `preview_error`. Analysis returns JSON report and Markdown. Explain requires `X-Allow-Cloud: true`; it revalidates and recomputes the bundle in a worker thread and returns the rules report even when AI is unavailable. `GET /api/examples` lists allowlisted examples; `GET /api/examples/{id}` loads one. The service binds to loopback by default and rejects non-loopback `serve` hosts. Public hosting needs separate authentication and security design.

The SDK request uses [Anthropic structured JSON output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). The SDK's [documented retry behavior](https://platform.claude.com/docs/en/api/errors) is capped at one retry; application code does not add another retry loop. Refusals, incomplete responses, malformed JSON, unknown evidence IDs and provider exceptions preserve the rules report with an explicit AI status. Referenced IDs establish that a record was supplied, not that the claim is semantically supported.

For each task, fetch the owner-designated remote's `main`, branch from that revision, implement and check one backlog item, inspect the staged diff, then push the task branch and open a PR into `main`. The owner merges. Continue dependent tasks only after the remote merge is verified. Never commit environment secrets or generated reports.
