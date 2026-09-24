using System.Text.Json;
using System.Text.Json.Serialization;

// Deliberate faults are selected only by the local scenario driver. No external webhook or payment API is used.
if (args.Length == 3 && args[0] == "export" && Modes.All.Contains(args[1]))
{
    var bundle = Scenario.Run(args[1]);
    await File.WriteAllTextAsync(args[2], JsonSerializer.Serialize(bundle.Bundle, Json.Options) + "\n");
    return;
}

if (args.Length == 2 && args[0] == "check" && Modes.All.Contains(args[1]))
{
    var ledger = Scenario.Run(args[1]).Ledger;
    if (args[1] == "fixed" && (ledger.Effects.Count != 1 || ledger.Versions.SequenceEqual(new[] { 1, 2 }) == false))
        throw new Exception("Fixed scenario violated business invariants");
    Console.WriteLine($"effects={ledger.Effects.Count}; versions={string.Join(',', ledger.Versions)}");
    return;
}

if (args.Length == 0)
{
    var builder = WebApplication.CreateBuilder(args);
    var app = builder.Build();
    app.MapGet("/", () => "Local synthetic payment-to-access sample. Use export <mode> <path>.");
    app.MapGet("/scenario/{mode}", (string mode) => Modes.All.Contains(mode)
        ? Results.Json(Scenario.Run(mode).Bundle)
        : Results.NotFound());
    app.Run("http://127.0.0.1:5084");
    return;
}

throw new ArgumentException("Use export <duplicate|stale|failure|fixed> <path>, check <mode>, or no args for loopback HTTP.");

static class Modes
{
    public static readonly HashSet<string> All = ["duplicate", "stale", "failure", "fixed"];
}

static class Json
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };
}

sealed class Ledger
{
    public HashSet<string> Effects { get; } = [];
    public List<int> Versions { get; } = [];
    public void Grant(string id) => Effects.Add(id);
    public void Apply(int version) => Versions.Add(version);
}

static class Scenario
{
    public static (object Bundle, Ledger Ledger) Run(string mode)
    {
        var ledger = new Ledger();
        var records = new List<Dictionary<string, object>>();
        void Add(string kind, int second, Dictionary<string, object>? fields = null)
        {
            var record = new Dictionary<string, object>
            {
                ["id"] = $"e{records.Count + 1}", ["occurred_at"] = $"2026-01-01T00:00:{second:00}Z",
                ["service"] = "access-service", ["kind"] = kind, ["message"] = kind.Replace('_', ' ')
            };
            if (fields is not null) foreach (var (key, value) in fields) record[key] = value;
            records.Add(record);
        }
        Dictionary<string, object> Event() => new() { ["provider"] = "sample-payments", ["event_id"] = "evt-1", ["attempt_id"] = "attempt-1" };
        Dictionary<string, object> Effect(string id) => new() { ["operation"] = "grant_access", ["entity_id"] = "order-1", ["business_key"] = "access-1", ["effect_id"] = id };
        Dictionary<string, object> State(int sequence, int version) => new() { ["operation"] = "update_access", ["entity_id"] = "order-1", ["sequence"] = sequence, ["entity_version"] = version };
        Add("event_received", 0, Event());
        var ack = Event(); ack["http_status"] = 200; Add("delivery_acknowledged", 1, ack);
        if (mode == "failure")
        {
            var failed = Event(); failed["error_code"] = "STORE_UNAVAILABLE"; Add("processing_failed", 2, failed);
        }
        else
        {
            Add("processing_started", 2, Event());
            ledger.Grant("grant-1"); Add("effect_committed", 3, Effect("grant-1"));
            if (mode == "duplicate") { ledger.Grant("grant-2"); Add("effect_committed", 4, Effect("grant-2")); }
            var first = mode == "stale" ? 2 : 1;
            var second = mode == "stale" ? 1 : 2;
            ledger.Apply(first); Add("state_applied", 5, State(1, first));
            ledger.Apply(second); Add("state_applied", 6, State(2, second));
            Add("processing_completed", 7, Event());
        }
        var bundle = new
        {
            schema_version = "1.0", incident_id = "sample-1", title = "Payment access webhook sample",
            invariants = new { single_effect_operations = new[] { "grant_access" }, monotonic_version_operations = new[] { "update_access" } },
            records
        };
        return (bundle, ledger);
    }
}
