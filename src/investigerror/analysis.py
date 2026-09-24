"""Shared offline analysis pipeline."""

from __future__ import annotations

import hashlib
import json

from . import __version__
from .correlation import timeline
from .models import IncidentBundle, InvestigationReport, ReportMetadata
from .redaction import sanitize
from .rules import RULE_VERSION, apply_rules


def analyze(bundle: IncidentBundle) -> InvestigationReport:
    safe = sanitize(bundle)
    canonical = json.dumps(safe.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    findings, limitations = apply_rules(safe)
    return InvestigationReport(
        incident_id=safe.incident_id,
        title=safe.title,
        description=safe.description,
        evidence=safe.records,
        timeline=timeline(safe),
        findings=findings,
        evidence_limitations=limitations,
        metadata=ReportMetadata(
            application_version=__version__,
            input_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            rule_version=RULE_VERSION,
            warnings=["Redaction is best-effort; inspect output before sharing."],
        ),
    )
