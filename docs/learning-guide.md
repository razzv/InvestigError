# Python walkthrough for C# developers

Follow one incident from `src/investigerror/cli.py` into `ingestion.py`, `analysis.py`, `rules.py` and `reporting.py`. Run the [setup and checks](development.md) first. The [architecture diagram](architecture.md) shows the whole path.

| Python in this project | Familiar C# idea | Where to look |
| --- | --- | --- |
| Pydantic `BaseModel` with fields and validators | DTO plus runtime validation and JSON contract | `models.py`, `ingestion.py` |
| Modules and packages | Files and namespaces/assemblies | `src/investigerror/`, `providers/` |
| `dict` and comprehensions | `Dictionary<TKey,TValue>` and LINQ projections | `context.py`, `evaluation.py` |
| Exceptions and `try`/`except` | Exceptions and `try`/`catch` | `ingestion.py`, `cli.py` |
| `with` context managers | `using` / `IDisposable` scope | tests and file access |
| A `Protocol` passed into a function | Small interface and injected implementation | `providers/base.py`, `explanation.py` |
| `async def` for HTTP requests; worker thread for blocking provider work | `async Task` and moving blocking work off the request loop | `api.py` |
| `pytest` fixtures, monkeypatch and fake providers | xUnit fixtures and test doubles | `tests/` |

Pydantic validates data at the boundary; type hints and mypy catch development mistakes but do not validate incoming JSON. `IncidentBundle` forbids unknown fields and validates timestamps, lengths and unique record IDs. A `Record` is then a typed object inside the pipeline. The generated JSON Schemas are public descriptions of these models; the runtime parser remains authoritative.

Python imports modules by package name. `pyproject.toml` maps the installed package under `src/` and exposes the `investigerror` command. The provider is a `Protocol`, so tests can supply a fake with the same `explain` method without constructing SDK responses. Exceptions at the input boundary become CLI exit codes or HTTP errors; provider failures become explicit report status while preserving rules findings.

The HTTP API uses `async def` to read a bounded request stream. The provider's synchronous call runs in a worker thread so a waiting call does not block local health or rules requests. The offline analysis functions stay synchronous and reusable by both CLI and API.

## Optional exercises

1. **Add one field:** Add an optional, bounded record field to `models.py`, regenerate schemas and validate a fixture. Expected: both JSON and generated schema accept it; unknown fields still fail.
2. **Implement one rule:** Add a narrowly evidenced rule in `rules.py` and a fixture with positive and negative cases. Expected: a finding cites stable record IDs only for the positive case.
3. **Add an edge-case fixture:** Add a repeated-delivery trace with one committed effect. Expected: no R1 duplicate-effect finding.
4. **Simulate a timeout:** Inject a provider fake that raises `ProviderFailure`. Expected: rules findings remain available, `ai_status` is `failed`, and the CLI exits nonzero (exit code 3 for an unsuccessful AI request).
5. **Trace a finding:** Analyze `example-002`, find an R1 `evidence_ids` entry in JSON, and locate that ID in the input. Expected: the cited records are the distinct committed effects, not the delivery records.

These are learning exercises; they are not required setup steps.
