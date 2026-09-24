"""Deterministic payment-to-access webhook demonstration; no real payment data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def bundle(mode: str) -> dict[str, object]:
    if mode not in {"duplicate", "stale", "failure", "fixed"}:
        raise ValueError("unknown mode")
    records: list[dict[str, object]] = []
    corrected = mode == "fixed"
    duplicate_input = mode in {"duplicate", "fixed"}
    stale_input = mode in {"stale", "fixed"}
    transient_failure = mode in {"failure", "fixed"}
    effects: dict[str, str] = {}
    versions: dict[str, int] = {}

    def add(kind: str, **fields: object) -> None:
        records.append(
            {
                "id": f"e{len(records) + 1}",
                "occurred_at": f"2026-01-01T00:00:{len(records):02d}Z",
                "service": "access-service",
                "kind": kind,
                "message": kind.replace("_", " "),
                **fields,
            }
        )

    common = {"provider": "sample-payments", "event_id": "evt-1", "attempt_id": "attempt-1"}

    def grant(effect_id: str) -> None:
        fields = {
            "operation": "grant_access",
            "entity_id": "order-1",
            "business_key": "access-1",
            "effect_id": effect_id,
        }
        if corrected and fields["business_key"] in effects:
            add("log", error_code="IDEMPOTENT_REPLAY", **fields)
            return
        effects[fields["business_key"]] = effect_id
        add("effect_committed", **fields)

    def apply(sequence: int, version: int) -> None:
        fields = {"operation": "update_access", "entity_id": "order-1", "sequence": sequence, "entity_version": version}
        if corrected and version < versions.get("order-1", -1):
            add("log", error_code="STALE_VERSION_REJECTED", **fields)
            return
        versions["order-1"] = version
        add("state_applied", **fields)

    add("event_received", **common)
    add("delivery_acknowledged", http_status=200, **common)
    add("processing_started", **common)
    if transient_failure:
        add("processing_failed", error_code="STORE_UNAVAILABLE", **common)
    if mode != "failure":
        if transient_failure:
            add("processing_started", **common)
        if duplicate_input:
            grant("grant-1")
            grant("grant-2")
        if stale_input:
            apply(1, 2)
            apply(2, 1)
        add("processing_completed", **common)
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
