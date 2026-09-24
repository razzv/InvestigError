"""Versioned input and output contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Kind(StrEnum):
    EVENT_RECEIVED = "event_received"
    DELIVERY_ACKNOWLEDGED = "delivery_acknowledged"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    EFFECT_COMMITTED = "effect_committed"
    STATE_APPLIED = "state_applied"
    LOG = "log"


class Invariants(ContractModel):
    single_effect_operations: list[str] = Field(default_factory=list)
    monotonic_version_operations: list[str] = Field(default_factory=list)

    @field_validator("single_effect_operations", "monotonic_version_operations")
    @classmethod
    def validate_operations(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 200 for value in values):
            raise ValueError("operations must be non-empty and at most 200 characters")
        if len(values) != len(set(values)):
            raise ValueError("operations must be unique")
        return values


class Record(ContractModel):
    id: str = Field(min_length=1, max_length=200)
    occurred_at: datetime
    service: str = Field(min_length=1, max_length=200)
    kind: Kind
    message: str = Field(max_length=2000)
    observed_at: datetime | None = None
    provider: str | None = Field(default=None, max_length=200)
    event_id: str | None = Field(default=None, max_length=200)
    attempt_id: str | None = Field(default=None, max_length=200)
    correlation_id: str | None = Field(default=None, max_length=200)
    entity_id: str | None = Field(default=None, max_length=200)
    operation: str | None = Field(default=None, max_length=200)
    business_key: str | None = Field(default=None, max_length=200)
    effect_id: str | None = Field(default=None, max_length=200)
    http_status: int | None = Field(default=None, ge=100, le=599)
    error_code: str | None = Field(default=None, max_length=200)
    entity_version: int | None = Field(default=None, ge=0)
    sequence: int | None = Field(default=None, ge=0)
    level: Literal["debug", "info", "warning", "error"] | None = None

    @field_validator("occurred_at", "observed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamp must include a timezone offset")
        return value


class IncidentBundle(ContractModel):
    schema_version: Literal["1.0"]
    incident_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    invariants: Invariants = Field(default_factory=Invariants)
    records: list[Record] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_record_ids(self) -> IncidentBundle:
        seen: set[str] = set()
        for index, record in enumerate(self.records):
            if record.id in seen:
                raise ValueError(f"records[{index}].id duplicates evidence ID {record.id!r}")
            seen.add(record.id)
        return self


class TimelineEntry(ContractModel):
    evidence_id: str
    occurred_at_utc: datetime
    simultaneous_with_previous: bool
    relationships: list[str] = Field(default_factory=list)


class Finding(ContractModel):
    finding_id: str
    rule_id: str
    severity: Literal["high", "medium", "info"]
    statement: str
    evidence_ids: list[str]
    limitations: list[str] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)


class ReportMetadata(ContractModel):
    application_version: str
    input_sha256: str
    rule_version: str
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None
    request_duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    selected_record_ids: list[str] = Field(default_factory=list)
    omitted_record_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InvestigationReport(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    incident_id: str
    title: str
    description: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    requested_mode: Literal["rules", "ai"] = "rules"
    ai_status: Literal["not_requested", "completed", "unavailable", "failed"] = "not_requested"
    evidence: list[Record]
    timeline: list[TimelineEntry]
    findings: list[Finding]
    evidence_limitations: list[str]
    ai_explanation: dict[str, object] | None = None
    metadata: ReportMetadata
