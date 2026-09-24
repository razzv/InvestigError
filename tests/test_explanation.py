import json
from pathlib import Path

import pytest

from investigerror.context import MAX_CONTEXT_CHARS, MAX_CONTEXT_RECORDS, select_context
from investigerror.explanation import AISettings, explain
from investigerror.ingestion import read_bundle
from investigerror.models import IncidentBundle
from investigerror.providers.base import ProviderFailure, ProviderResult
from investigerror.redaction import sanitize

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "incidents"
SETTINGS = AISettings(api_key="synthetic-test-key", model="test-model")


def valid_output(evidence_ids: list[str] | None = None) -> str:
    return json.dumps({
        "summary": "The capture shows an acknowledged delivery and a processing failure.",
        "hypotheses": [{
            "category": "processing_failure_after_ack",
            "statement": "Processing failed after acknowledgement in this capture.",
            "evidence_ids": evidence_ids if evidence_ids is not None else ["a2", "a3"],
            "reasoning_summary": "Both records refer to the same delivery attempt.",
            "missing_evidence": ["Later recovery records"],
            "verification_steps": ["Inspect the retry and recovery logs."],
        }],
        "alternatives": [{
            "statement": "Recovery may have occurred outside the capture.",
            "evidence_ids": [],
            "missing_evidence": ["Recovery records"],
        }],
        "next_steps": ["Check the final business outcome."],
        "limitations": ["Uncaptured activity is unknown."],
    })


class FakeProvider:
    def __init__(self, text: str | None = None, failure: Exception | None = None, stop_reason: str = "end_turn"):
        self.text = text if text is not None else valid_output()
        self.failure = failure
        self.stop_reason = stop_reason
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def explain(self, context: str, system_prompt: str, schema: dict[str, object]) -> ProviderResult:
        self.calls.append((context, system_prompt, schema))
        if self.failure:
            raise self.failure
        return ProviderResult(
            text=self.text, model="test-model", stop_reason=self.stop_reason,
            duration_ms=12, input_tokens=123, output_tokens=45,
        )


def test_mock_success_has_validated_references_and_usage() -> None:
    bundle = read_bundle(EXAMPLES / "example-001.json")
    fake = FakeProvider()
    report = explain(bundle, allow_cloud=True, provider=fake, settings=SETTINGS)
    assert report.ai_status == "completed"
    assert report.ai_explanation is not None
    assert report.ai_explanation.hypotheses[0].evidence_ids == ["a2", "a3"]
    assert report.metadata.selected_record_ids == ["a1", "a2", "a3"]
    assert report.metadata.selected_record_count == 3
    assert report.metadata.omitted_record_count == 0
    assert (report.metadata.input_tokens, report.metadata.output_tokens) == (123, 45)
    assert report.metadata.estimated_cost is None
    context, prompt, schema = fake.calls[0]
    assert json.loads(context)["records"][0]["id"] == "a1"
    assert "untrusted" in prompt.lower()
    assert "hypotheses" in schema["properties"]


@pytest.mark.parametrize(
    ("settings", "allow_cloud", "warning"),
    [
        (SETTINGS, False, "--allow-cloud"),
        (AISettings(api_key=None, model="test-model"), True, "ANTHROPIC_API_KEY"),
        (AISettings(api_key="synthetic-test-key", model=None), True, "AI_MODEL"),
    ],
)
def test_unavailable_never_calls_provider(settings: AISettings, allow_cloud: bool, warning: str) -> None:
    fake = FakeProvider()
    report = explain(
        read_bundle(EXAMPLES / "example-001.json"),
        allow_cloud=allow_cloud, provider=fake, settings=settings,
    )
    assert report.ai_status == "unavailable"
    assert report.ai_explanation is None
    assert report.findings[0].rule_id == "R3"
    assert warning in report.metadata.warnings[-1]
    assert report.metadata.omitted_record_count == len(report.evidence)
    assert not fake.calls


@pytest.mark.parametrize(
    ("failure", "warning"),
    [
        (ProviderFailure("Anthropic request timed out."), "timed out"),
        (ProviderFailure("Anthropic rate limit or spend limit was reached."), "rate limit"),
    ],
)
def test_provider_failure_keeps_rules_report_without_retry(failure: Exception, warning: str) -> None:
    fake = FakeProvider(failure=failure)
    report = explain(
        read_bundle(EXAMPLES / "example-001.json"),
        allow_cloud=True, provider=fake, settings=SETTINGS,
    )
    assert report.ai_status == "failed"
    assert report.ai_explanation is None
    assert report.findings[0].rule_id == "R3"
    assert warning in report.metadata.warnings[-1]
    assert len(fake.calls) == 1


@pytest.mark.parametrize(
    "text",
    [
        "{bad JSON",
        valid_output(["unknown-id"]),
        json.dumps({**json.loads(valid_output()), "unexpected": "field"}),
    ],
)
def test_bad_output_is_rejected_without_retry(text: str) -> None:
    fake = FakeProvider(text=text)
    report = explain(
        read_bundle(EXAMPLES / "example-001.json"),
        allow_cloud=True, provider=fake, settings=SETTINGS,
    )
    assert report.ai_status == "failed"
    assert report.ai_explanation is None
    assert report.findings[0].rule_id == "R3"
    assert len(fake.calls) == 1
    assert report.metadata.input_tokens == 123


def test_alternative_must_cite_selected_evidence_or_name_missing_evidence() -> None:
    for alternative in (
        {"statement": "Unsupported claim", "evidence_ids": ["unknown-id"], "missing_evidence": []},
        {"statement": "Unsupported claim", "evidence_ids": [], "missing_evidence": []},
    ):
        value = json.loads(valid_output())
        value["alternatives"] = [alternative]
        fake = FakeProvider(text=json.dumps(value))
        report = explain(
            read_bundle(EXAMPLES / "example-001.json"),
            allow_cloud=True, provider=fake, settings=SETTINGS,
        )
        assert report.ai_status == "failed"
        assert report.ai_explanation is None
        assert len(fake.calls) == 1


def test_truncated_response_is_not_accepted() -> None:
    fake = FakeProvider(stop_reason="max_tokens")
    report = explain(
        read_bundle(EXAMPLES / "example-001.json"),
        allow_cloud=True, provider=fake, settings=SETTINGS,
    )
    assert report.ai_status == "failed"
    assert report.ai_explanation is None
    assert len(fake.calls) == 1


def test_injection_fixture_is_data_and_redacted_before_provider() -> None:
    fake = FakeProvider(text=valid_output(["f1"]))
    report = explain(
        read_bundle(EXAMPLES / "example-006.json"),
        allow_cloud=True, provider=fake, settings=SETTINGS,
    )
    assert report.ai_status == "completed"
    context, prompt, _ = fake.calls[0]
    assert "Ignore previous instructions" in context
    assert "synthetic-fixture-secret" not in context
    assert "[S]" in context
    assert "untrusted evidence" in prompt
    assert "synthetic-fixture-secret" not in report.model_dump_json()


def test_provider_text_is_redacted_before_report() -> None:
    value = json.loads(valid_output())
    value["summary"] = "Observed token=synthetic-provider-secret in the response."
    report = explain(
        read_bundle(EXAMPLES / "example-001.json"),
        allow_cloud=True, provider=FakeProvider(text=json.dumps(value)), settings=SETTINGS,
    )
    assert report.ai_status == "completed"
    assert "synthetic-provider-secret" not in report.model_dump_json()


def test_context_prefers_complete_finding_evidence_and_reports_omissions() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    for index in range(110):
        data["records"].append({
            "id": f"extra-{index:03}", "occurred_at": "2026-09-24T09:00:03Z",
            "service": "unrelated-service", "kind": "log", "message": "Unrelated log",
        })
    fake = FakeProvider()
    report = explain(IncidentBundle.model_validate(data), allow_cloud=True, provider=fake, settings=SETTINGS)
    context = json.loads(fake.calls[0][0])
    assert len(fake.calls[0][0]) <= MAX_CONTEXT_CHARS
    assert report.metadata.selected_record_count <= MAX_CONTEXT_RECORDS
    assert report.metadata.omitted_record_count > 0
    assert {"a2", "a3"} <= set(report.metadata.selected_record_ids)
    assert set(context["metadata"]["omitted_record_ids"]) == set(report.metadata.omitted_record_ids)
    assert len(context["records"]) == report.metadata.selected_record_count


def test_citation_to_report_record_omitted_from_provider_request_is_rejected() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    for index in range(110):
        data["records"].append({
            "id": f"extra-{index:03}", "occurred_at": "2026-09-24T09:00:03Z",
            "service": "unrelated-service", "kind": "log", "message": "Unrelated log",
        })
    fake = FakeProvider(text=valid_output(["extra-109"]))
    report = explain(IncidentBundle.model_validate(data), allow_cloud=True, provider=fake, settings=SETTINGS)
    assert "extra-109" in {record.id for record in report.evidence}
    assert "extra-109" in report.metadata.omitted_record_ids
    assert report.ai_status == "failed"
    assert report.ai_explanation is None
    assert len(fake.calls) == 1


@pytest.mark.parametrize("count", [25, 101])
def test_oversized_required_evidence_prevents_partial_provider_request(count: int) -> None:
    data = json.loads((EXAMPLES / "example-002.json").read_text(encoding="utf-8"))
    seed = data["records"][1]
    data["records"] = [
        {**seed, "id": f"effect-{index}", "effect_id": f"grant-{index}",
         "message": "x" * (2000 if count == 25 else 1)}
        for index in range(count)
    ]
    fake = FakeProvider()
    report = explain(IncidentBundle.model_validate(data), allow_cloud=True, provider=fake, settings=SETTINGS)
    assert report.ai_status == "unavailable"
    assert any(finding.rule_id == "R1" for finding in report.findings)
    assert report.metadata.selected_record_count == 0
    assert report.metadata.omitted_record_count == count
    assert not fake.calls


def test_context_builder_never_sends_unredacted_bundle() -> None:
    data = json.loads((EXAMPLES / "example-001.json").read_text(encoding="utf-8"))
    data["records"][0]["message"] += " token=synthetic-context-secret"
    bundle = IncidentBundle.model_validate(data)
    safe = sanitize(bundle)
    from investigerror.analysis import analyze

    selected = select_context(safe, analyze(safe))
    assert "synthetic-context-secret" not in selected.text
