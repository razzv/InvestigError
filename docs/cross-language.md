# Cross-language sample

The local ASP.NET Core sample in `examples/dotnet/InvestigError.Sample` simulates a payment-to-access webhook. It has no real payment provider, credentials or customer data. Its deterministic driver supports `duplicate`, `stale`, `failure` and `fixed`. The first three deliberately violate a single-effect invariant, a monotonic version invariant or a processing outcome. The fixed mode applies one effect and versions 1 then 2; `check fixed` asserts these business invariants. Run without arguments to serve a loopback demonstration endpoint on port 5084.

From the repository root, for example in PowerShell:

```powershell
dotnet run --project examples/dotnet/InvestigError.Sample -- export duplicate "$((Get-Location).Path)/artifacts/dotnet-duplicate.json"
uv run python examples/exporters/python_exporter.py --mode duplicate --out artifacts/python-duplicate.json
uv run investigerror analyze artifacts/dotnet-duplicate.json --mode rules --out artifacts/dotnet-report.json
uv run investigerror analyze artifacts/python-duplicate.json --mode rules --out artifacts/python-report.json
dotnet run --project examples/dotnet/InvestigError.Sample -- check fixed
```

Create `artifacts/` first if needed. Both exporters emit the same V1 contract with deterministic IDs and timestamps. The test suite runs all four modes through the shared parser and analyzer and compares normalized bundles and findings. The .NET SDK 9 is required to run the C# sample; tests skip its execution if the SDK is absent. No analyzer logic branches on export language.
