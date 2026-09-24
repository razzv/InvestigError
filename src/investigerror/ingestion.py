"""Bounded JSON and JSONL ingestion with location-aware errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import IncidentBundle

MAX_BYTES = 2 * 1024 * 1024


class InputError(ValueError):
    """An input could not be parsed or validated."""


def read_bundle(path: Path) -> IncidentBundle:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    return parse_bundle(raw, path.suffix.lower())


def parse_bundle(raw: bytes, suffix: str) -> IncidentBundle:
    if len(raw) > MAX_BYTES:
        raise InputError(f"input exceeds {MAX_BYTES} byte limit")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError(f"invalid UTF-8 at byte {exc.start}") from exc
    record_lines: list[int] = []
    if suffix == ".json":
        try:
            value = json.loads(content)
        except json.JSONDecodeError as exc:
            raise InputError(f"JSON line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    elif suffix == ".jsonl":
        value, record_lines = _parse_jsonl(content)
    else:
        raise InputError("expected a .json or .jsonl file")
    try:
        return IncidentBundle.model_validate(value)
    except ValidationError as exc:
        messages = []
        for issue in exc.errors():
            location = issue["loc"]
            prefix = ""
            if suffix == ".jsonl" and len(location) > 1 and location[0] == "records":
                index = location[1]
                if isinstance(index, int) and index < len(record_lines):
                    prefix = f"JSONL line {record_lines[index]}, "
            messages.append(f"{prefix}{'.'.join(map(str, location))}: {issue['msg']}")
        details = "; ".join(messages)
        raise InputError(details) from exc


def _parse_jsonl(content: str) -> tuple[dict[str, Any], list[int]]:
    manifest: dict[str, Any] | None = None
    records: list[Any] = []
    record_lines: list[int] = []
    for line_no, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            envelope = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InputError(f"JSONL line {line_no}, column {exc.colno}: {exc.msg}") from exc
        if not isinstance(envelope, dict):
            raise InputError(f"JSONL line {line_no}: envelope must be an object")
        if manifest is None:
            if set(envelope) != {"type", "bundle"} or envelope["type"] != "manifest":
                raise InputError(f"JSONL line {line_no}: expected manifest envelope first")
            if not isinstance(envelope["bundle"], dict) or "records" in envelope["bundle"]:
                raise InputError(f"JSONL line {line_no}: manifest bundle must omit records")
            manifest = envelope["bundle"]
        else:
            if set(envelope) != {"type", "record"} or envelope["type"] != "record":
                raise InputError(f"JSONL line {line_no}: expected record envelope")
            records.append(envelope["record"])
            record_lines.append(line_no)
            if len(records) > 1000:
                raise InputError(f"JSONL line {line_no}: exceeds 1000 record limit")
    if manifest is None:
        raise InputError("JSONL requires one manifest first")
    return {**manifest, "records": records}, record_lines
