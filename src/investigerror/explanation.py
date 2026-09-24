"""Optional explanation orchestration and independent output validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import resources
from typing import Any

from pydantic import ValidationError

from .analysis import analyze
from .context import PROMPT_VERSION, ContextLimitError, select_context
from .models import AIExplanation, Alternative, Hypothesis, IncidentBundle, InvestigationReport
from .providers.anthropic import AnthropicProvider
from .providers.base import ExplanationProvider, ProviderFailure
from .redaction import redact_text, sanitize


@dataclass(frozen=True)
class AISettings:
    api_key: str | None
    model: str | None
    timeout_seconds: float = 30.0
    max_output_tokens: int = 3000

    @classmethod
    def from_env(cls) -> AISettings:
        try:
            timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
            tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "3000"))
        except ValueError as exc:
            raise ValueError("AI_TIMEOUT_SECONDS and AI_MAX_OUTPUT_TOKENS must be numeric.") from exc
        if not 0 < timeout <= 600 or not 1 <= tokens <= 20_000:
            raise ValueError("AI timeout or output token budget is outside supported bounds.")
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", "").strip() or None,
            model=os.getenv("AI_MODEL", "").strip() or None,
            timeout_seconds=timeout,
            max_output_tokens=tokens,
        )


def _redact_output(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_output(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_output(item) for key, item in value.items()}
    return value


def _validate_explanation(text: str, selected_ids: list[str]) -> AIExplanation:
    try:
        explanation = AIExplanation.model_validate_json(text)
    except ValidationError as exc:
        raise ValueError("Provider output did not match the explanation schema.") from exc
    allowed = set(selected_ids)

    def check_references(item: Hypothesis | Alternative) -> None:
        if not set(item.evidence_ids) <= allowed:
            raise ValueError("Provider output cited an unknown or omitted evidence ID.")
        if not item.evidence_ids and not item.missing_evidence:
            raise ValueError("A hypothesis or alternative needs evidence or explicit missing evidence.")

    for item in explanation.hypotheses:
        check_references(item)
    for alternative in explanation.alternatives:
        check_references(alternative)
    return AIExplanation.model_validate(_redact_output(explanation.model_dump()))


def explain(
    bundle: IncidentBundle,
    *,
    allow_cloud: bool,
    provider: ExplanationProvider | None = None,
    settings: AISettings | None = None,
) -> InvestigationReport:
    """Keep the rules report even when AI is unavailable or invalid."""
    safe = sanitize(bundle)
    report = analyze(safe)
    report.requested_mode = "ai"
    report.ai_status = "unavailable"
    report.metadata.provider = "anthropic"
    report.metadata.prompt_version = PROMPT_VERSION
    report.metadata.omitted_record_ids = [record.id for record in safe.records]
    report.metadata.omitted_record_count = len(safe.records)
    if not allow_cloud:
        report.metadata.warnings.append("AI mode requires --allow-cloud; no data was transmitted.")
        return report
    try:
        config = settings or AISettings.from_env()
    except ValueError as exc:
        report.metadata.warnings.append(str(exc))
        return report
    if not config.api_key:
        report.metadata.warnings.append("ANTHROPIC_API_KEY is not configured; no data was transmitted.")
        return report
    if not config.model:
        report.metadata.warnings.append("AI_MODEL is not configured; no data was transmitted.")
        return report
    report.metadata.model = config.model
    try:
        context = select_context(safe, report)
    except ContextLimitError as exc:
        report.metadata.warnings.append(str(exc))
        return report
    report.metadata.selected_record_ids = context.selected_ids
    report.metadata.omitted_record_ids = context.omitted_ids
    report.metadata.selected_record_count = len(context.selected_ids)
    report.metadata.omitted_record_count = len(context.omitted_ids)
    prompt = resources.files("investigerror").joinpath("prompts/explain-v1.txt").read_text(encoding="utf-8")
    try:
        adapter = provider or AnthropicProvider(
            config.api_key, config.model, config.timeout_seconds, config.max_output_tokens,
        )
        result = adapter.explain(context.text, prompt, AIExplanation.model_json_schema())
    except ProviderFailure as exc:
        report.ai_status = "failed"
        report.metadata.warnings.append(redact_text(str(exc)))
        return report
    except Exception:
        report.ai_status = "failed"
        report.metadata.warnings.append("Provider request failed unexpectedly.")
        return report
    report.metadata.request_duration_ms = result.duration_ms
    report.metadata.input_tokens = result.input_tokens
    report.metadata.output_tokens = result.output_tokens
    report.metadata.model = result.model
    if result.stop_reason != "end_turn":
        report.ai_status = "failed"
        report.metadata.warnings.append("Provider did not complete the explanation response.")
        return report
    try:
        report.ai_explanation = _validate_explanation(result.text, context.selected_ids)
    except ValueError as exc:
        report.ai_status = "failed"
        report.metadata.warnings.append(str(exc))
        return report
    report.ai_status = "completed"
    report.metadata.warnings.append("Evidence references were checked; semantic support requires human review.")
    return report
