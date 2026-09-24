# Development

Use Python 3.12 or newer and uv. Local checks were run with Python 3.13.2 on Windows PowerShell.

```sh
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python scripts/generate_schemas.py
uv run investigerror validate examples/incidents/example-001.json
uv run investigerror analyze examples/incidents/example-001.json --mode rules --out artifacts/report.json
```

Run from another working directory with the installed command in `.venv/Scripts/investigerror.exe` on Windows or `.venv/bin/investigerror` on macOS/Linux. Outputs belong under gitignored `artifacts/`; use `--overwrite` to replace them. `validate` exits 2 on invalid input. `analyze` exits 2 on invalid input or an existing output, and exits 3 for a requested AI explanation that could not run after writing the rules report. A successful report exits 0 even if it contains a fault finding.

Core flow: `ingestion.py` parses and validates; `redaction.py` masks known secrets; `correlation.py` builds the timeline; `rules.py` makes checkable findings; `analysis.py` assembles the report; `reporting.py` renders safe Markdown; `cli.py` provides commands. The JSON Schemas in `schemas/` are generated from `models.py`.

For each task, fetch the owner-designated remote's `main`, branch from that revision, implement and check one backlog item, inspect the staged diff, then push the task branch and open a PR into `main`. The owner merges. Continue dependent tasks only after the remote merge is verified. Never commit environment secrets or generated reports.
