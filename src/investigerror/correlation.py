"""Stable timeline and scoped, exact identifier relationships."""

from __future__ import annotations

from datetime import UTC

from .models import IncidentBundle, Record, TimelineEntry


def timeline(bundle: IncidentBundle) -> list[TimelineEntry]:
    ordered = sorted(bundle.records, key=lambda r: (r.occurred_at, r.id))
    prior: list[Record] = []
    result: list[TimelineEntry] = []
    for record in ordered:
        links: list[str] = []
        for other in prior:
            reasons = relationship_reasons(other, record)
            if reasons:
                links.append(f"{other.id}: {', '.join(reasons)}")
        result.append(
            TimelineEntry(
                evidence_id=record.id,
                occurred_at_utc=record.occurred_at.astimezone(UTC),
                simultaneous_with_previous=bool(prior and prior[-1].occurred_at == record.occurred_at),
                relationships=links,
            )
        )
        prior.append(record)
    return result


def relationship_reasons(a: Record, b: Record) -> list[str]:
    reasons: list[str] = []
    if a.correlation_id and a.correlation_id == b.correlation_id:
        reasons.append("same correlation_id")
    if a.service != b.service:
        return reasons
    if a.provider and a.provider == b.provider and a.event_id and a.event_id == b.event_id:
        reasons.append("same service/provider/event_id")
    if a.attempt_id and a.attempt_id == b.attempt_id and a.event_id and a.event_id == b.event_id:
        if a.provider == b.provider:
            reasons.append("same service/provider/event_id/attempt_id")
    if all((a.operation, a.entity_id, a.business_key)) and (
        a.operation, a.entity_id, a.business_key
    ) == (b.operation, b.entity_id, b.business_key):
        reasons.append("same service/operation/entity_id/business_key")
    return reasons
