# Cross-language sample

The local ASP.NET Core sample in `examples/dotnet/InvestigError.Sample` simulates a payment-to-access webhook. It has no real payment provider, credentials or customer data. Its deterministic driver supports `duplicate`, `stale`, `failure` and `fixed`. The first three deliberately commit a duplicate effect, apply a lower version, or leave processing failed. The fixed mode receives the same duplicate grant attempts, out-of-order versions (2 then 1), and transient failure. Its handler rejects the replay by business key, rejects the stale version, and records a later completion. The exported logs identify rejected attempts without labeling them committed. `check fixed` asserts the ledger outcomes. The deterministic R3 observation remains in the fixed report because the earlier failure is real and the later completion is visible. Run without arguments to serve a loopback demonstration endpoint on port 5084.

From the repository root, for example in PowerShell:

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
dotnet run --project examples/dotnet/InvestigError.Sample -- export duplicate "$((Get-Location).Path)/artifacts/dotnet-duplicate.json"
uv run python examples/exporters/python_exporter.py --mode duplicate --out artifacts/python-duplicate.json
uv run investigerror analyze artifacts/dotnet-duplicate.json --mode rules --out artifacts/dotnet-report.json
uv run investigerror analyze artifacts/python-duplicate.json --mode rules --out artifacts/python-report.json
dotnet run --project examples/dotnet/InvestigError.Sample -- check fixed
```

Both exporters emit the same V1 contract with deterministic IDs and timestamps. The test suite runs all four modes through the shared parser and analyzer and compares normalized bundles and findings. The local machine had SDKs 8 and 9 installed, so this sample targets .NET 9 as a compatible fallback to the brief's .NET 10 default; CI installs SDK 9. Tests skip C# execution if the SDK is absent. No analyzer logic branches on export language.
