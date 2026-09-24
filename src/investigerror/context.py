"""Select complete finding evidence before bounded surrounding context."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .correlation import relationship_reasons
from .models import IncidentBundle, InvestigationReport, Record

MAX_CONTEXT_RECORDS = 100
MAX_CONTEXT_CHARS = 40_000
PROMPT_VERSION = "explain-v1"


class ContextLimitError(ValueError):
    """The required finding evidence does not fit the provider request."""


@dataclass(frozen=True)
class SelectedContext:
    text: str
    selected_ids: list[str]
    omitted_ids: list[str]


def select_context(bundle: IncidentBundle, report: InvestigationReport) -> SelectedContext:
    """Bundle must already be sanitized by the shared analysis pipeline."""
    by_id = {record.id: record for record in bundle.records}
    ordered = [by_id[entry.evidence_id] for entry in report.timeline]
    required_ids = {item for finding in report.findings for item in finding.evidence_ids}
    required = [record for record in ordered if record.id in required_ids]
    if len(required) != len(required_ids):
        raise ContextLimitError("Finding evidence is missing from the sanitized bundle.")
    if len(required) > MAX_CONTEXT_RECORDS:
        raise ContextLimitError("Required finding evidence exceeds 100 records; narrow the bundle.")

    def serialize(selected: list[Record]) -> SelectedContext:
        selected_set = {record.id for record in selected}
        in_order = [record for record in ordered if record.id in selected_set]
        omitted = [record.id for record in ordered if record.id not in selected_set]
        payload = {
            "schema_version": bundle.schema_version,
            "incident_id": bundle.incident_id,
            "title": bundle.title,
            "description": bundle.description,
            "invariants": bundle.invariants.model_dump(mode="json"),
            "records": [record.model_dump(mode="json", exclude_none=True) for record in in_order],
            "findings": [finding.model_dump(mode="json") for finding in report.findings],
            "metadata": {
                "input_sha256": report.metadata.input_sha256,
                "rule_version": report.metadata.rule_version,
                "prompt_version": PROMPT_VERSION,
                "selected_record_count": len(in_order),
                "omitted_record_count": len(omitted),
                "selected_record_ids": [record.id for record in in_order],
                "omitted_record_ids": omitted,
            },
        }
        return SelectedContext(
            text=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            selected_ids=[record.id for record in in_order],
            omitted_ids=omitted,
        )

    selected = required.copy()
    result = serialize(selected)
    if len(result.text) > MAX_CONTEXT_CHARS:
        raise ContextLimitError("Required finding evidence exceeds 40,000 characters; narrow the bundle.")

    remaining = [record for record in ordered if record.id not in required_ids]
    related = [
        record for record in remaining
        if any(relationship_reasons(record, evidence) for evidence in required)
    ]
    related_ids = {record.id for record in related}
    candidates = related + [record for record in remaining if record.id not in related_ids]
    for record in candidates:
        if len(selected) >= MAX_CONTEXT_RECORDS:
            break
        candidate = serialize([*selected, record])
        if len(candidate.text) <= MAX_CONTEXT_CHARS:
            selected.append(record)
            result = candidate
    return result
