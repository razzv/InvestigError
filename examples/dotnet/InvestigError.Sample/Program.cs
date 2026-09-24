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
    if (args[1] == "fixed" && (ledger.Effects.Count != 1 || !ledger.Versions.SequenceEqual(new[] { 2 })
        || ledger.RejectedEffects != 1 || ledger.RejectedVersions != 1 || !ledger.Recovered))
        throw new Exception("Corrected handler failed to reject duplicate/stale input or recover processing");
    if (args[1] == "duplicate" && ledger.Effects.Count != 2)
        throw new Exception("Faulty duplicate demonstration did not commit two effects");
    if (args[1] == "stale" && !ledger.Versions.SequenceEqual(new[] { 2, 1 }))
        throw new Exception("Faulty state demonstration did not apply a stale version");
    Console.WriteLine($"effects={ledger.Effects.Count}; versions={string.Join(',', ledger.Versions)}; " +
        $"rejected_effects={ledger.RejectedEffects}; rejected_versions={ledger.RejectedVersions}; recovered={ledger.Recovered}");
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
    private readonly HashSet<string> businessKeys = [];
    public List<string> Effects { get; } = [];
    public List<int> Versions { get; } = [];
    public int RejectedEffects { get; private set; }
    public int RejectedVersions { get; private set; }
    public bool Recovered { get; set; }

    public bool Grant(string businessKey, string effectId, bool corrected)
    {
        if (corrected && !businessKeys.Add(businessKey)) { RejectedEffects++; return false; }
        businessKeys.Add(businessKey);
        Effects.Add(effectId);
        return true;
    }

    public bool Apply(int version, bool corrected)
    {
        if (corrected && Versions.Count > 0 && version < Versions.Max()) { RejectedVersions++; return false; }
        Versions.Add(version);
        return true;
    }
}

static class Scenario
{
    public static (object Bundle, Ledger Ledger) Run(string mode)
    {
        var ledger = new Ledger();
        var corrected = mode == "fixed";
        var duplicateInput = mode is "duplicate" or "fixed";
        var staleInput = mode is "stale" or "fixed";
        var transientFailure = mode is "failure" or "fixed";
        var records = new List<Dictionary<string, object>>();
        void Add(string kind, Dictionary<string, object>? fields = null)
        {
            var record = new Dictionary<string, object>
            {
                ["id"] = $"e{records.Count + 1}", ["occurred_at"] = $"2026-01-01T00:00:{records.Count:00}Z",
                ["service"] = "access-service", ["kind"] = kind, ["message"] = kind.Replace('_', ' ')
            };
            if (fields is not null) foreach (var (key, value) in fields) record[key] = value;
            records.Add(record);
        }
        Dictionary<string, object> Event() => new() { ["provider"] = "sample-payments", ["event_id"] = "evt-1", ["attempt_id"] = "attempt-1" };
        Dictionary<string, object> Effect() => new() { ["operation"] = "grant_access", ["entity_id"] = "order-1", ["business_key"] = "access-1" };
        Dictionary<string, object> State(int sequence, int version) => new() { ["operation"] = "update_access", ["entity_id"] = "order-1", ["sequence"] = sequence, ["entity_version"] = version };
        void Grant(string effectId)
        {
            var fields = Effect();
            fields["effect_id"] = effectId;
            if (ledger.Grant("access-1", effectId, corrected))
            {
                Add("effect_committed", fields);
            }
            else
            {
                fields["error_code"] = "IDEMPOTENT_REPLAY";
                Add("log", fields);
            }
        }
        void Apply(int sequence, int version)
        {
            var fields = State(sequence, version);
            if (ledger.Apply(version, corrected)) Add("state_applied", fields);
            else { fields["error_code"] = "STALE_VERSION_REJECTED"; Add("log", fields); }
        }
        Add("event_received", Event());
        var ack = Event(); ack["http_status"] = 200; Add("delivery_acknowledged", ack);
        Add("processing_started", Event());
        if (transientFailure)
        {
            var failed = Event(); failed["error_code"] = "STORE_UNAVAILABLE";
            Add("processing_failed", failed);
        }
        if (mode != "failure")
        {
            if (transientFailure) Add("processing_started", Event());
            if (duplicateInput) { Grant("grant-1"); Grant("grant-2"); }
            if (staleInput) { Apply(1, 2); Apply(2, 1); }
            Add("processing_completed", Event());
            ledger.Recovered = transientFailure;
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
