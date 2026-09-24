"""Contract and evaluation behavior across the two reference exporters."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from investigerror.analysis import analyze
from investigerror.cli import app
from investigerror.evaluation import evaluate
from investigerror.explanation import AISettings
from investigerror.ingestion import read_bundle
from investigerror.models import Finding
from investigerror.providers.base import ProviderFailure, ProviderResult

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evaluation"
DOTNET = ROOT / "examples" / "dotnet" / "InvestigError.Sample" / "InvestigError.Sample.csproj"
PYTHON = ROOT / "examples" / "exporters" / "python_exporter.py"


def test_corpus_is_fresh_and_offline_score_reproduces(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_corpus.py")], check=True)
    result = evaluate(CORPUS)
    assert result["case_count"] == 18
    assert result["rules"]["quality_gate_passed"]
    assert result["model_comparison"]["status"] == "unmeasured"
    assert all(value["fp"] == value["fn"] == 0 for value in result["rules"]["metrics"].values())
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["cases"]:
        input_text = (CORPUS / entry["input"]).read_text(encoding="utf-8")
        label = json.loads((CORPUS / entry["label"]).read_text(encoding="utf-8"))
        assert "required" not in input_text and "prohibited" not in input_text
        assert not {"template", "variant", "split", "label"} & set(json.loads(input_text))
        assert label["case_id"] == entry["case_id"]
        assert len(read_bundle(CORPUS / entry["input"]).records) >= 1
    assert len(evaluate(CORPUS, "holdout")["rules"]["cases"]) >= 5


@pytest.mark.parametrize("mutation", ["extra_first", "missing_group", "extra_group"])
def test_all_same_rule_evidence_groups_are_scored(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    original = analyze

    def changed(bundle: object) -> object:
        report = original(bundle)  # type: ignore[arg-type]
        if report.incident_id == "case-001" and mutation == "extra_first":
            report.findings.insert(
                0,
                Finding(
                    finding_id="extra",
                    rule_id="R1",
                    severity="high",
                    statement="Unsupported extra",
                    evidence_ids=["r1"],
                ),
            )
        if report.incident_id == "case-018":
            if mutation == "missing_group":
                report.findings.pop()
            if mutation == "extra_group":
                report.findings.append(
                    Finding(
                        finding_id="extra",
                        rule_id="R1",
                        severity="high",
                        statement="Unsupported extra",
                        evidence_ids=["r1"],
                    )
                )
        return report

    monkeypatch.setattr("investigerror.evaluation.analyze", changed)
    result = evaluate(CORPUS)
    assert not result["rules"]["quality_gate_passed"]
    affected = "case-001" if mutation == "extra_first" else "case-018"
    row = next(row for row in result["rules"]["cases"] if row["case_id"] == affected)
    assert row["missing_findings"] if mutation == "missing_group" else row["unexpected_findings"]
    assert result["rules"]["metrics"]["R1"]["fp" if mutation != "missing_group" else "fn"] == 1


@pytest.mark.parametrize("error", ["Anthropic request timed out.", "Anthropic rate limit was reached."])
def test_cli_preserves_partial_live_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, error: str) -> None:
    class FailingProvider:
        calls = 0

        def __init__(self, *args: object) -> None:
            pass

        def explain(self, context: str, prompt: str, schema: dict[str, object]) -> ProviderResult:
            self.calls += 1
            if self.calls == 2:
                raise ProviderFailure(error)
            answer = {
                "summary": "Needs review",
                "hypotheses": [],
                "alternatives": [],
                "next_steps": [],
                "limitations": [],
            }
            return ProviderResult(json.dumps(answer), "mock-model", "end_turn", 5, 11, 7)

    monkeypatch.setattr(
        "investigerror.evaluation.AISettings.from_env", lambda: AISettings("synthetic-key", "mock-model")
    )
    monkeypatch.setattr("investigerror.evaluation.AnthropicProvider", FailingProvider)
    output = tmp_path / "partial.json"
    result = CliRunner().invoke(
        app, ["evaluate", "--mode", "live", "--allow-cloud", "--corpus", str(CORPUS), "--out", str(output)]
    )
    assert result.exit_code == 3
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["rules"]["quality_gate_passed"]
    assert saved["case_count"] == 18
    assert saved["model_comparison"]["status"] == "partial"
    rows = saved["model_comparison"]["review_sheet"]
    assert [row["request_status"] for row in rows] == ["completed", "failed"]
    assert rows[0]["input_tokens"] == 11 and rows[1]["input_tokens"] is None
    assert error in rows[1]["error"]
    assert "failed" in output.with_suffix(".md").read_text(encoding="utf-8")


def test_exact_non_ascii_provider_payload_stays_bounded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    copied = tmp_path / "corpus"
    shutil.copytree(CORPUS, copied)
    path = copied / "inputs" / "case-001.json"
    incident = json.loads(path.read_text(encoding="utf-8"))
    for index in range(12):
        incident["records"].append(
            {
                "id": f"unicode-{index}",
                "occurred_at": f"2026-02-01T00:00:{index + 2:02d}Z",
                "service": "access-service",
                "kind": "log",
                "message": "漢" * 2000,
            }
        )
    path.write_text(json.dumps(incident, ensure_ascii=False), encoding="utf-8")
    captured: list[str] = []

    class CaptureProvider:
        def __init__(self, *args: object) -> None:
            pass

        def explain(self, context: str, prompt: str, schema: dict[str, object]) -> ProviderResult:
            captured.append(context)
            answer = {
                "summary": "Needs review",
                "hypotheses": [],
                "alternatives": [],
                "next_steps": [],
                "limitations": [],
            }
            return ProviderResult(json.dumps(answer), "mock-model", "end_turn", 1)

    monkeypatch.setattr(
        "investigerror.evaluation.AISettings.from_env", lambda: AISettings("synthetic-key", "mock-model")
    )
    monkeypatch.setattr("investigerror.evaluation.AnthropicProvider", CaptureProvider)
    evaluate(copied, "train", live=True)
    generic, focused = captured[:2]
    assert "漢" in generic and "漢" in focused
    assert len(generic) <= 40_000 and len(focused) <= 40_000
    assert json.loads(generic)["records"] == json.loads(focused)["records"]
    assert len(json.loads(generic)["records"]) <= 100


def test_live_comparison_payloads_share_records_and_exclude_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeProvider:
        def __init__(self, *args: object) -> None:
            pass

        def explain(self, context: str, prompt: str, schema: dict[str, object]) -> ProviderResult:
            payload = json.loads(context)
            calls.append(payload)
            assert "required" not in context and "prohibited" not in context
            assert "template" not in payload and "split" not in payload
            assert schema
            answer = {
                "summary": "Needs review",
                "hypotheses": [],
                "alternatives": [],
                "next_steps": [],
                "limitations": [],
            }
            return ProviderResult(json.dumps(answer), "mock-model", "end_turn", 1, 10, 10)

    monkeypatch.setattr(
        "investigerror.evaluation.AISettings.from_env", lambda: AISettings("synthetic-key", "mock-model")
    )
    monkeypatch.setattr("investigerror.evaluation.AnthropicProvider", FakeProvider)
    result = evaluate(CORPUS, "holdout", live=True)
    assert len(calls) == 2 * result["case_count"]
    for generic, focused in zip(calls[::2], calls[1::2], strict=True):
        assert generic["records"] == focused["records"]
        assert "findings" not in generic and "findings" in focused
    assert all(row["valid_references"] for row in result["model_comparison"]["review_sheet"])


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("duplicate", {"R1"}),
        ("stale", {"R2"}),
        ("failure", {"R3"}),
        ("fixed", {"R3"}),
    ],
)
def test_python_exporter(mode: str, expected: set[str], tmp_path: Path) -> None:
    output = tmp_path / "python.json"
    subprocess.run([sys.executable, str(PYTHON), "--mode", mode, "--out", str(output)], check=True)
    assert {item.rule_id for item in analyze(read_bundle(output)).findings} == expected


@pytest.mark.skipif(shutil.which("dotnet") is None, reason=".NET SDK unavailable")
@pytest.mark.parametrize("mode", ["duplicate", "stale", "failure", "fixed"])
def test_dotnet_export_matches_python_and_fixed_invariants(mode: str, tmp_path: Path) -> None:
    dotnet_out = tmp_path / "dotnet.json"
    python_out = tmp_path / "python.json"
    subprocess.run(
        ["dotnet", "run", "--project", str(DOTNET), "--", "export", mode, str(dotnet_out)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run([sys.executable, str(PYTHON), "--mode", mode, "--out", str(python_out)], check=True)
    dotnet_bundle, python_bundle = read_bundle(dotnet_out), read_bundle(python_out)
    assert dotnet_bundle.model_dump(mode="json") == python_bundle.model_dump(mode="json")
    dotnet_findings = [(finding.rule_id, finding.evidence_ids) for finding in analyze(dotnet_bundle).findings]
    python_findings = [(finding.rule_id, finding.evidence_ids) for finding in analyze(python_bundle).findings]
    assert dotnet_findings == python_findings
    if mode == "fixed":
        check = subprocess.run(
            ["dotnet", "run", "--project", str(DOTNET), "--", "check", "fixed"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "effects=1; versions=2; rejected_effects=1; rejected_versions=1; recovered=True" in check.stdout
        kinds = [record.kind.value for record in dotnet_bundle.records]
        assert kinds.count("effect_committed") == 1 and kinds.count("state_applied") == 1
        assert {record.error_code for record in dotnet_bundle.records if record.kind.value == "log"} == {
            "IDEMPOTENT_REPLAY",
            "STALE_VERSION_REJECTED",
        }
        replay = next(record for record in dotnet_bundle.records if record.error_code == "IDEMPOTENT_REPLAY")
        rejected_state = next(
            record for record in dotnet_bundle.records if record.error_code == "STALE_VERSION_REJECTED"
        )
        assert replay.effect_id == "grant-2" and rejected_state.entity_version == 1
        assert "later processing completion" in analyze(dotnet_bundle).findings[0].statement
