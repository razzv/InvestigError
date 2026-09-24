import json
from pathlib import Path

from fastapi.testclient import TestClient

from investigerror.api import app
from investigerror.ingestion import MAX_BYTES

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "incidents" / "example-001.json"
client = TestClient(app)


def upload(path: str, raw: bytes, name: str = "incident.json", **fields: str):
    return client.post(path, files={"file": (name, raw)}, data=fields)


def test_examples_rules_and_exports_share_evidence() -> None:
    listed = client.get("/api/examples").json()
    assert any(item["id"] == "example-001" for item in listed)
    example = client.get("/api/examples/example-001")
    assert example.status_code == 200
    assert client.get("/api/examples/../api").status_code != 200
    result = upload("/api/analyze", example.content)
    assert result.status_code == 200
    data = result.json()
    assert data["report"]["ai_status"] == "not_requested"
    assert {finding["rule_id"] for finding in data["report"]["findings"]} == {"R3"}
    ids = {record["id"] for record in data["report"]["evidence"]}
    assert set(data["report"]["findings"][0]["evidence_ids"]) <= ids
    assert "a2" in data["markdown"]


def test_preview_is_sanitized_selected_provider_payload() -> None:
    incident = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    incident["records"][0]["message"] = "Bearer secret-token token=SYNTHETIC_SECRET user@example.com"
    result = upload("/api/validate", json.dumps(incident).encode())
    assert result.status_code == 200
    data = result.json()
    assert data["bundle"]["records"][0]["message"] == "[S] [S] [E]"
    serialized = json.dumps(data)
    assert "SYNTHETIC_SECRET" not in serialized
    assert "user@example.com" not in serialized
    assert data["provider_context"]["metadata"]["selected_record_count"] > 0
    assert data["provider_context"]["records"]


def test_ai_needs_consent_and_missing_credentials_preserve_rules(monkeypatch) -> None:
    raw = EXAMPLE.read_bytes()
    assert upload("/api/explain", raw).status_code == 400
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    result = upload("/api/explain", raw, allow_cloud="true")
    assert result.status_code == 200
    report = result.json()["report"]
    assert report["requested_mode"] == "ai"
    assert report["ai_status"] == "unavailable"
    assert report["findings"][0]["rule_id"] == "R3"
    assert "no data was transmitted" in " ".join(report["metadata"]["warnings"])


def test_jsonl_and_explicit_explain_route(monkeypatch) -> None:
    from investigerror.analysis import analyze

    seen = []

    def fake_explain(bundle, *, allow_cloud):
        seen.append((bundle.incident_id, allow_cloud))
        return analyze(bundle)

    monkeypatch.setattr("investigerror.api.explain", fake_explain)
    raw = (EXAMPLE.parent / "example-001.jsonl").read_bytes()
    validated = upload("/api/validate", raw, name="incident.jsonl")
    assert validated.status_code == 200
    result = upload("/api/explain", raw, name="incident.jsonl", allow_cloud="true")
    assert result.status_code == 200
    assert seen == [(validated.json()["bundle"]["incident_id"], True)]


def test_invalid_upload_and_cross_origin_are_rejected_without_echoing_secret() -> None:
    invalid = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    invalid["records"][0]["id"] = "token=SYNTHETIC_SECRET"
    invalid["records"][1]["id"] = "token=SYNTHETIC_SECRET"
    result = upload("/api/validate", json.dumps(invalid).encode())
    assert result.status_code == 422
    assert "records[1].id" in result.json()["detail"]
    assert "SYNTHETIC_SECRET" not in result.text
    assert upload("/api/validate", b"x" * (MAX_BYTES + 1)).status_code == 422
    assert upload("/api/analyze", b"{}", name="bad.txt").status_code == 422
    cross = client.post(
        "/api/analyze", files={"file": ("incident.json", EXAMPLE.read_bytes())},
        headers={"origin": "https://hostile.example"},
    )
    assert cross.status_code == 403
    assert TestClient(app, base_url="http://hostile.example").get("/health").status_code == 400


def test_static_browser_assets_and_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert "InvestigError" in client.get("/").text
    assert "textContent" in client.get("/static/app.js").text
    assert client.get("/static/styles.css").status_code == 200


def test_packaged_examples_match_documented_fixtures() -> None:
    from investigerror.api import EXAMPLES

    for path in EXAMPLES.values():
        assert path.read_bytes() == (EXAMPLE.parent / path.name).read_bytes()
