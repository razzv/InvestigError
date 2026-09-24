"""Deterministic checks over supplied evidence only."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Literal

from .models import Finding, IncidentBundle, Kind, Record

RULE_VERSION = "1"


def _finding(
    rule: str, severity: Literal["high", "medium", "info"], statement: str, records: Iterable[Record],
    limitations: list[str], checks: list[str],
) -> Finding:
    ids = sorted({record.id for record in records})
    return Finding(
        finding_id=f"{rule.lower()}-{'-'.join(ids)}",
        rule_id=rule,
        severity=severity,
        statement=statement,
        evidence_ids=ids,
        limitations=limitations,
        next_checks=checks,
    )


def apply_rules(bundle: IncidentBundle) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    limitations: list[str] = []
    findings.extend(_duplicate_effects(bundle, limitations))
    findings.extend(_stale_state(bundle, limitations))
    findings.extend(_acknowledged_failure(bundle, limitations))
    findings.extend(_repeated_deliveries(bundle))
    if not findings:
        if limitations or not any(r.kind == Kind.PROCESSING_COMPLETED for r in bundle.records):
            findings.append(_finding(
                "INSUFFICIENT_EVIDENCE", "info",
                "The supplied records do not establish a checked failure or a complete healthy trace.",
                bundle.records, ["Uncaptured activity may exist."],
                ["Capture downstream processing and committed outcomes."],
            ))
        else:
            findings.append(_finding(
                "NO_ISSUE_OBSERVED", "info",
                "No checked violation is observed in the supplied records.", bundle.records,
                ["This does not establish that the entire integration is healthy."],
                ["Check whether the capture covers the expected business outcome."],
            ))
    return findings, list(dict.fromkeys(limitations))


def _duplicate_effects(bundle: IncidentBundle, limitations: list[str]) -> list[Finding]:
    declared = set(bundle.invariants.single_effect_operations)
    groups: dict[tuple[str, str, str, str], list[Record]] = defaultdict(list)
    for record in bundle.records:
        if record.kind != Kind.EFFECT_COMMITTED:
            continue
        if record.operation not in declared:
            limitations.append("R1 cannot check an effect without a declared single-effect operation.")
        elif not all((record.service, record.entity_id, record.business_key, record.effect_id)):
            limitations.append("R1 cannot check an effect missing entity_id, business_key or effect_id.")
        else:
            assert record.operation and record.entity_id and record.business_key
            groups[(record.service, record.operation, record.entity_id, record.business_key)].append(record)
    findings = []
    for records in groups.values():
        distinct = {r.effect_id for r in records}
        if len(distinct) > 1:
            findings.append(_finding(
                "R1", "high",
                "Distinct committed effects violate the declared single-effect operation invariant.",
                records, ["This checks only effects present in the bundle."],
                ["Inspect the idempotency guard and committed side-effect store."],
            ))
    return findings


def _stale_state(bundle: IncidentBundle, limitations: list[str]) -> list[Finding]:
    declared = set(bundle.invariants.monotonic_version_operations)
    groups: dict[tuple[str, str, str], list[Record]] = defaultdict(list)
    for record in bundle.records:
        if record.kind != Kind.STATE_APPLIED:
            continue
        if record.operation not in declared:
            limitations.append("R2 cannot check state without a declared monotonic-version operation.")
        elif record.entity_id is None or record.sequence is None or record.entity_version is None:
            limitations.append("R2 requires entity_id, sequence and entity_version on each applied state.")
        else:
            assert record.operation
            groups[(record.service, record.operation, record.entity_id)].append(record)
    findings = []
    for records in groups.values():
        by_sequence: dict[int, list[Record]] = defaultdict(list)
        for record in records:
            assert record.sequence is not None
            by_sequence[record.sequence].append(record)
        if any(len({r.entity_version for r in group}) > 1 for group in by_sequence.values()):
            limitations.append("R2 has conflicting entity versions at the same local sequence.")
            continue
        ordered = sorted(records, key=lambda r: (r.sequence if r.sequence is not None else -1, r.id))
        highest: Record | None = None
        for record in ordered:
            if highest and record.sequence != highest.sequence and (
                record.entity_version is not None and highest.entity_version is not None
                and record.entity_version < highest.entity_version
            ):
                findings.append(_finding(
                    "R2", "high",
                    "A later local sequence applied a lower entity version, violating the declared invariant.",
                    [highest, record], ["Local sequence is supplied by the exporter."],
                    ["Inspect version guards and out-of-order state application."],
                ))
            if highest is None or (record.entity_version is not None and
                                   highest.entity_version is not None and
                                   record.entity_version > highest.entity_version):
                highest = record
    return findings


def _acknowledged_failure(bundle: IncidentBundle, limitations: list[str]) -> list[Finding]:
    groups: dict[tuple[str, str | None, str, str], list[Record]] = defaultdict(list)
    for record in bundle.records:
        if record.kind not in {
            Kind.DELIVERY_ACKNOWLEDGED, Kind.PROCESSING_FAILED, Kind.PROCESSING_COMPLETED,
            Kind.PROCESSING_STARTED,
        }:
            continue
        if not record.event_id or not record.attempt_id:
            limitations.append("R3 requires event_id and attempt_id to connect delivery and processing.")
            continue
        groups[(record.service, record.provider, record.event_id, record.attempt_id)].append(record)
    findings = []
    for records in groups.values():
        acks = [r for r in records if r.kind == Kind.DELIVERY_ACKNOWLEDGED and
                r.http_status is not None and 200 <= r.http_status < 300]
        failures = [r for r in records if r.kind == Kind.PROCESSING_FAILED]
        completions = [r for r in records if r.kind == Kind.PROCESSING_COMPLETED]
        if acks and failures:
            evidence = acks + failures + completions
            recovered = any(c.occurred_at > f.occurred_at for c in completions for f in failures)
            statement = "A 2xx delivery acknowledgement and processing failure are both observed."
            if recovered:
                statement += " A later processing completion is also observed."
            findings.append(_finding(
                "R3", "medium", statement, evidence,
                ["The capture cannot establish whether recovery happened outside these records."],
                ["Inspect retry, recovery and final business outcome records."],
            ))
        elif acks and not any(r.kind in {Kind.PROCESSING_STARTED, Kind.PROCESSING_COMPLETED} for r in records):
            findings.append(_finding(
                "MISSING_DOWNSTREAM", "info",
                "A 2xx acknowledgement is observed without downstream processing evidence in this capture.",
                acks, ["Missing logs do not prove processing was lost."],
                ["Capture processing records for this service, event and attempt."],
            ))
    return findings


def _repeated_deliveries(bundle: IncidentBundle) -> list[Finding]:
    groups: dict[tuple[str, str, str], list[Record]] = defaultdict(list)
    for record in bundle.records:
        if record.kind == Kind.EVENT_RECEIVED and record.provider and record.event_id:
            groups[(record.service, record.provider, record.event_id)].append(record)
    return [
        _finding(
            "REPEATED_DELIVERY", "info", "Repeated event delivery is observed.", records,
            ["Retries alone do not establish duplicate business effects."],
            ["Check idempotency and committed effects for this event."],
        )
        for records in groups.values() if len({r.attempt_id for r in records}) > 1
    ]
