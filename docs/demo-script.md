# Local demo script (2–3 minutes)

Prepare with `uv sync --locked --extra dev`, then run `uv run investigerror evaluate --mode rules --split all --out artifacts/evaluation.json --overwrite`. Start `uv run investigerror serve --host 127.0.0.1 --port 8000` in a separate terminal and open `http://127.0.0.1:8000`. No API key is needed. All examples are synthetic.

1. **Failing case (about 40 seconds):** Load bundled `example-002`, validate, then run rules. Point to R1 and its evidence IDs. Select each linked record: `b2` and `b4` are two distinct `effect_committed` records for one declared single-effect operation. The repeated delivery records alone are insufficient for this finding.
2. **Corrected behavior (about 40 seconds):** Before the demo, export a fixed bundle. In PowerShell, run `dotnet run --project examples/dotnet/InvestigError.Sample -- export fixed "$((Get-Location).Path)/artifacts/dotnet-fixed.json"`; in macOS/Linux, run `dotnet run --project examples/dotnet/InvestigError.Sample -- export fixed "$(pwd)/artifacts/dotnet-fixed.json"`. Or use `uv run python examples/exporters/python_exporter.py --mode fixed --out artifacts/python-fixed.json`. Load the exported fixed bundle in the browser and run rules. The replay and stale update are rejected, and a later completion is recorded. An R3 observation can remain because the earlier acknowledged failure happened; recovery does not erase evidence.
3. **Insufficient evidence (about 30 seconds):** Load `example-005`. Show the acknowledgement and the missing downstream capture limitation. Avoid claiming the job was lost.
4. **Evaluation (about 30 seconds):** Open `artifacts/evaluation.md` from the offline command. Show the synthetic quality gate and the unreviewed live-model fields. Explain that the current corpus is a regression set, not a production benchmark.

Optional closing line: cloud explanation requires a separate preview, credentials, selected model and explicit consent. Keep it off for the offline demo.
