import json
from pathlib import Path

from investigerror.models import IncidentBundle, InvestigationReport

ROOT = Path(__file__).resolve().parents[1]


def test_generated_schemas_are_current() -> None:
    for name, model in (
        ("incident-bundle", IncidentBundle),
        ("investigation-report", InvestigationReport),
    ):
        committed = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
        assert committed == model.model_json_schema()
