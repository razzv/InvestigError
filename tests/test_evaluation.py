"""Contract and evaluation behavior across the two reference exporters."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from investigerror.analysis import analyze
from investigerror.evaluation import evaluate
from investigerror.explanation import AISettings
from investigerror.ingestion import read_bundle
from investigerror.providers.base import ProviderResult

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evaluation"
DOTNET = ROOT / "examples" / "dotnet" / "InvestigError.Sample" / "InvestigError.Sample.csproj"
PYTHON = ROOT / "examples" / "exporters" / "python_exporter.py"


def test_corpus_is_fresh_and_offline_score_reproduces(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_corpus.py")], check=True)
    result = evaluate(CORPUS)
    assert result["case_count"] == 17
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
            answer = {"summary": "Needs review", "hypotheses": [], "alternatives": [],
                      "next_steps": [], "limitations": []}
            return ProviderResult(json.dumps(answer), "mock-model", "end_turn", 1, 10, 10)

    monkeypatch.setattr("investigerror.evaluation.AISettings.from_env",
                        lambda: AISettings("synthetic-key", "mock-model"))
    monkeypatch.setattr("investigerror.evaluation.AnthropicProvider", FakeProvider)
    result = evaluate(CORPUS, "holdout", live=True)
    assert len(calls) == 2 * result["case_count"]
    for generic, focused in zip(calls[::2], calls[1::2], strict=True):
        assert generic["records"] == focused["records"]
        assert "findings" not in generic and "findings" in focused
    assert all(row["valid_references"] for row in result["model_comparison"]["review_sheet"])


@pytest.mark.parametrize("mode,expected", [
    ("duplicate", {"R1"}), ("stale", {"R2"}), ("failure", {"R3"}),
    ("fixed", {"NO_ISSUE_OBSERVED"}),
])
def test_python_exporter(mode: str, expected: set[str], tmp_path: Path) -> None:
    output = tmp_path / "python.json"
    subprocess.run([sys.executable, str(PYTHON), "--mode", mode, "--out", str(output)], check=True)
    assert {item.rule_id for item in analyze(read_bundle(output)).findings} == expected


@pytest.mark.skipif(shutil.which("dotnet") is None, reason=".NET SDK unavailable")
@pytest.mark.parametrize("mode", ["duplicate", "stale", "failure", "fixed"])
def test_dotnet_export_matches_python_and_fixed_invariants(mode: str, tmp_path: Path) -> None:
    dotnet_out = tmp_path / "dotnet.json"
    python_out = tmp_path / "python.json"
    subprocess.run(["dotnet", "run", "--project", str(DOTNET), "--", "export", mode, str(dotnet_out)],
                   check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, str(PYTHON), "--mode", mode, "--out", str(python_out)], check=True)
    dotnet_bundle, python_bundle = read_bundle(dotnet_out), read_bundle(python_out)
    assert dotnet_bundle.model_dump(mode="json") == python_bundle.model_dump(mode="json")
    dotnet_findings = [(finding.rule_id, finding.evidence_ids) for finding in analyze(dotnet_bundle).findings]
    python_findings = [(finding.rule_id, finding.evidence_ids) for finding in analyze(python_bundle).findings]
    assert dotnet_findings == python_findings
    if mode == "fixed":
        check = subprocess.run(["dotnet", "run", "--project", str(DOTNET), "--", "check", "fixed"],
                               check=True, capture_output=True, text=True)
        assert "effects=1; versions=1,2" in check.stdout
