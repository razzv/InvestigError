import json
from pathlib import Path

import pytest

from investigerror.analysis import analyze
from investigerror.ingestion import MAX_BYTES, InputError, parse_bundle, read_bundle
from investigerror.models import IncidentBundle
from investigerror.reporting import markdown

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "incidents"


@pytest.mark.parametrize(
    ("name", "required", "excluded"),
    [
        ("example-001", {"R3"}, {"R1", "R2"}),
        ("example-002", {"R1", "REPEATED_DELIVERY"}, {"R2", "R3"}),
        ("example-003", {"R2"}, {"R1", "R3"}),
        ("example-004", {"NO_ISSUE_OBSERVED"}, {"R1", "R2", "R3"}),
        ("example-005", {"MISSING_DOWNSTREAM"}, {"R3"}),
    ],
)
def test_examples(name: str, required: set[str], excluded: set[str]) -> None:
    report = analyze(read_bundle(EXAMPLES / f"{name}.json"))
    rules = {finding.rule_id for finding in report.findings}
    assert required <= rules
    assert not rules & excluded
    ids = {record.id for record in report.evidence}
    assert all(set(finding.evidence_ids) <= ids for finding in report.findings)


def test_jsonl_equivalence() -> None:
    source = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    records = source.pop("records")
    lines = [json.dumps({"type": "manifest", "bundle": source})]
    lines.extend(json.dumps({"type": "record", "record": r}) for r in records)
    parsed = parse_bundle(("\n".join(lines) + "\n").encode(), ".jsonl")
    original = read_bundle(EXAMPLES / "example-001.json")
    assert parsed == original
    assert analyze(parsed).model_dump(exclude={"generated_at"}) == analyze(original).model_dump(
        exclude={"generated_at"}
    )
    assert read_bundle(EXAMPLES / "example-001.jsonl") == original


def test_retries_and_repeated_effect_log_are_not_duplicate_effects() -> None:
    data = json.loads((EXAMPLES / "example-002.json").read_text(encoding="utf-8"))
    data["records"][-1]["effect_id"] = "grant_001"
    report = analyze(IncidentBundle.model_validate(data))
    assert "R1" not in {finding.rule_id for finding in report.findings}
    assert "REPEATED_DELIVERY" in {finding.rule_id for finding in report.findings}


def test_scoped_identifiers_do_not_merge_providers_or_services() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    data["records"][2]["provider"] = "other-payments"
    report = analyze(IncidentBundle.model_validate(data))
    assert "R3" not in {finding.rule_id for finding in report.findings}
    assert not any("same service/provider/event_id" in link for link in report.timeline[2].relationships)


def test_stale_requires_declared_invariant_and_local_sequence() -> None:
    data = json.loads((EXAMPLES / "example-003.json").read_text(encoding="utf-8"))
    data["invariants"]["monotonic_version_operations"] = []
    assert "R2" not in {f.rule_id for f in analyze(IncidentBundle.model_validate(data)).findings}
    data["invariants"]["monotonic_version_operations"] = ["set_access_state"]
    data["records"][1]["sequence"] = None
    report = analyze(IncidentBundle.model_validate(data))
    assert "R2" not in {f.rule_id for f in report.findings}
    assert any("R2 requires" in item for item in report.evidence_limitations)


def test_recovery_does_not_erase_observed_failure() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    recovered = {**data["records"][2], "id": "a4", "kind": "processing_completed",
                 "occurred_at": "2026-09-24T09:00:03Z", "message": "Recovered"}
    data["records"].append(recovered)
    finding = next(f for f in analyze(IncidentBundle.model_validate(data)).findings if f.rule_id == "R3")
    assert set(finding.evidence_ids) == {"a2", "a3", "a4"}
    assert "later processing completion" in finding.statement


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda d: d.pop("title"), "title"),
        (lambda d: d["records"][0].update(occurred_at="2026-09-24T09:00:00"), "timezone"),
        (lambda d: d["records"][1].update(id="a1"), "duplicates evidence ID"),
        (lambda d: d["records"][0].update(mystery="value"), "mystery"),
        (lambda d: d.update(schema_version="2.0"), "schema_version"),
    ],
)
def test_invalid_contract(change: object, error: str) -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    change(data)  # type: ignore[operator]
    with pytest.raises(InputError, match=error):
        parse_bundle(json.dumps(data).encode(), ".json")


def test_size_utf8_and_record_limits() -> None:
    with pytest.raises(InputError, match="byte limit"):
        parse_bundle(b" " * (MAX_BYTES + 1), ".json")
    with pytest.raises(InputError, match="UTF-8"):
        parse_bundle(b"\xff", ".json")
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    data["records"] = [{**data["records"][0], "id": str(i)} for i in range(1001)]
    with pytest.raises(InputError, match="1000"):
        parse_bundle(json.dumps(data).encode(), ".json")


def test_redaction_and_markdown_escaping() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    data["description"] = "Contact ada@example.com; token=private123"
    data["records"][0]["message"] = "<script>alert(1)</script> [click](javascript:alert(1)) Bearer secret123"
    data["records"][0]["entity_id"] = "ada@example.com"
    report = analyze(IncidentBundle.model_validate(data))
    serialized = report.model_dump_json()
    assert "ada@example.com" not in serialized
    assert "private123" not in serialized
    assert "secret123" not in serialized
    rendered = markdown(report)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "[click](javascript:" not in rendered


def test_jsonl_line_error() -> None:
    raw = b'{"type":"manifest","bundle":{"schema_version":"1.0"}}\n{"type":"record", bad}\n'
    with pytest.raises(InputError, match="line 2"):
        parse_bundle(raw, ".jsonl")


def test_jsonl_record_validation_location() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    record = data.pop("records")[0]
    record["occurred_at"] = "2026-09-24T09:00:00"
    raw = "\n".join([
        json.dumps({"type": "manifest", "bundle": data}),
        "",
        json.dumps({"type": "record", "record": record}),
    ]).encode()
    with pytest.raises(InputError, match="JSONL line 3, records.0.occurred_at"):
        parse_bundle(raw, ".jsonl")


def test_redacted_record_id_does_not_collide_with_existing_id() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    data["records"][0]["id"] = "ada@example.com"
    data["records"][1]["id"] = "redacted_id_1"
    report = analyze(IncidentBundle.model_validate(data))
    ids = [record.id for record in report.evidence]
    assert len(ids) == len(set(ids))
    assert "ada@example.com" not in report.model_dump_json()
