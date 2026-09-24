"""Best-effort redaction before reports and future provider calls."""

from __future__ import annotations

import re

from .models import IncidentBundle

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
SECRET = re.compile(
    r"\b(?:sk_(?:test|live)_[A-Za-z0-9]+|sk-ant-[A-Za-z0-9_-]+|gh[pousr]_[A-Za-z0-9]+|"
    r"(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+)",
    re.IGNORECASE,
)


def redact_text(value: str) -> str:
    value = BEARER.sub("[REDACTED_CREDENTIAL]", value)
    value = SECRET.sub("[REDACTED_CREDENTIAL]", value)
    return EMAIL.sub("[REDACTED_EMAIL]", value)


def sanitize(bundle: IncidentBundle) -> IncidentBundle:
    """Apply stable aliases to sensitive identifiers and mask free text."""
    data = bundle.model_dump(mode="python")
    aliases: dict[str, str] = {}
    identifier_keys = (
        "id", "service", "provider", "event_id", "attempt_id", "correlation_id",
        "entity_id", "operation", "business_key", "effect_id", "error_code",
    )
    reserved = {str(data["incident_id"])}
    for record in data["records"]:
        reserved.update(str(record[key]) for key in identifier_keys if record[key] is not None)
    for key in ("single_effect_operations", "monotonic_version_operations"):
        reserved.update(data["invariants"][key])

    def clean_identifier(value: str | None) -> str | None:
        if value is None:
            return None
        if redact_text(value) != value:
            if value not in aliases:
                candidate = f"redacted_id_{len(aliases) + 1}"
                while candidate in reserved:
                    candidate += "_"
                aliases[value] = candidate
                reserved.add(candidate)
            return aliases[value]
        return value

    data["incident_id"] = clean_identifier(data["incident_id"])
    data["title"] = redact_text(data["title"])
    if data["description"] is not None:
        data["description"] = redact_text(data["description"])
    for key in ("single_effect_operations", "monotonic_version_operations"):
        data["invariants"][key] = [clean_identifier(v) for v in data["invariants"][key]]
    for record in data["records"]:
        record["message"] = redact_text(record["message"])
        for key in identifier_keys:
            record[key] = clean_identifier(record[key])
    return IncidentBundle.model_validate(data)
