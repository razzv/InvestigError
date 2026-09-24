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
