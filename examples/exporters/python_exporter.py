"""Deterministic payment-to-access webhook demonstration; no real payment data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def bundle(mode: str) -> dict[str, object]:
    if mode not in {"duplicate", "stale", "failure", "fixed"}:
        raise ValueError("unknown mode")
    records: list[dict[str, object]] = []

    def add(kind: str, second: int, **fields: object) -> None:
        records.append(
            {
                "id": f"e{len(records) + 1}",
                "occurred_at": f"2026-01-01T00:00:{second:02d}Z",
                "service": "access-service",
                "kind": kind,
                "message": kind.replace("_", " "),
                **fields,
            }
        )

    common = {"provider": "sample-payments", "event_id": "evt-1", "attempt_id": "attempt-1"}
    add("event_received", 0, **common)
    add("delivery_acknowledged", 1, http_status=200, **common)
    if mode == "failure":
        add("processing_failed", 2, error_code="STORE_UNAVAILABLE", **common)
    else:
        add("processing_started", 2, **common)
        effect = {"operation": "grant_access", "entity_id": "order-1", "business_key": "access-1"}
        add("effect_committed", 3, effect_id="grant-1", **effect)
        if mode == "duplicate":
            add("effect_committed", 4, effect_id="grant-2", **effect)
        state = {"operation": "update_access", "entity_id": "order-1"}
        if mode == "stale":
            add("state_applied", 5, sequence=1, entity_version=2, **state)
            add("state_applied", 6, sequence=2, entity_version=1, **state)
        else:
            add("state_applied", 5, sequence=1, entity_version=1, **state)
            add("state_applied", 6, sequence=2, entity_version=2, **state)
        add("processing_completed", 7, **common)
    return {
        "schema_version": "1.0",
        "incident_id": "sample-1",
        "title": "Payment access webhook sample",
        "invariants": {"single_effect_operations": ["grant_access"], "monotonic_version_operations": ["update_access"]},
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["duplicate", "stale", "failure", "fixed"])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(bundle(args.mode), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
