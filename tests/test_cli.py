import json
from pathlib import Path

from typer.testing import CliRunner

from investigerror.cli import app

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "incidents" / "example-001.json"
runner = CliRunner()


def test_cli_writes_both_reports_and_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = runner.invoke(app, ["analyze", str(EXAMPLE), "--out", str(output)])
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ai_status"] == "not_requested"
    assert {finding["rule_id"] for finding in report["findings"]} == {"R3"}
    assert "a2" in output.with_suffix(".md").read_text(encoding="utf-8")
    assert runner.invoke(app, ["analyze", str(EXAMPLE), "--out", str(output)]).exit_code == 2
    assert runner.invoke(
        app, ["analyze", str(EXAMPLE), "--out", str(output), "--overwrite"]
    ).exit_code == 0


def test_unavailable_ai_preserves_rules_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = runner.invoke(app, ["analyze", str(EXAMPLE), "--mode", "ai", "--out", str(output)])
    assert result.exit_code == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["requested_mode"] == "ai"
    assert report["ai_status"] == "unavailable"
    assert report["findings"][0]["rule_id"] == "R3"


def test_duplicate_secret_id_is_not_echoed_by_cli(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    secret = "token=SYNTHETIC_REVIEW_SECRET"
    data["records"][0]["id"] = secret
    data["records"][1]["id"] = secret
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    for args in (["validate", str(source)], ["analyze", str(source), "--out", str(tmp_path / "out.json")]):
        result = runner.invoke(app, args)
        assert result.exit_code == 2
        assert "duplicate" in result.output.lower()
        assert "records[1].id" in result.output
        assert secret not in result.output


def test_ai_cli_writes_validated_explanation_with_mock_provider(
    tmp_path: Path, monkeypatch,
) -> None:
    from investigerror.providers.base import ProviderResult

    payload = {
        "summary": "A processing failure is observed.",
        "hypotheses": [{
            "category": "processing_failure_after_ack", "statement": "Processing failed.",
            "evidence_ids": ["a2", "a3"], "reasoning_summary": "Same attempt.",
            "missing_evidence": [], "verification_steps": ["Inspect retry logs."],
        }],
        "alternatives": [], "next_steps": ["Check recovery."],
        "limitations": ["Later activity is unknown."],
    }

    class MockProvider:
        def explain(self, context, system_prompt, schema):
            return ProviderResult(json.dumps(payload), "test-model", "end_turn", 5, 10, 20)

    monkeypatch.setattr("investigerror.explanation.AnthropicProvider", lambda *args: MockProvider())
    output = tmp_path / "ai.json"
    result = runner.invoke(
        app,
        ["analyze", str(EXAMPLE), "--mode", "ai", "--allow-cloud", "--out", str(output)],
        env={"ANTHROPIC_API_KEY": "synthetic-test-key", "AI_MODEL": "test-model"},
    )
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ai_status"] == "completed"
    assert report["ai_explanation"]["hypotheses"][0]["evidence_ids"] == ["a2", "a3"]
    assert "A processing failure is observed" in output.with_suffix(".md").read_text(encoding="utf-8")


def test_ai_cli_missing_key_exits_nonzero_and_writes_rules(tmp_path: Path) -> None:
    output = tmp_path / "ai.json"
    result = runner.invoke(
        app,
        ["analyze", str(EXAMPLE), "--mode", "ai", "--allow-cloud", "--out", str(output)],
        env={"ANTHROPIC_API_KEY": "", "AI_MODEL": "test-model"},
    )
    assert result.exit_code == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ai_status"] == "unavailable"
    assert report["findings"][0]["rule_id"] == "R3"
