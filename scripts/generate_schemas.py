"""Refresh generated JSON Schemas from Pydantic models."""

import json
from pathlib import Path

from investigerror.models import IncidentBundle, InvestigationReport

ROOT = Path(__file__).resolve().parents[1]
for name, model in (
    ("incident-bundle", IncidentBundle),
    ("investigation-report", InvestigationReport),
):
    target = ROOT / "schemas" / f"{name}.schema.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
