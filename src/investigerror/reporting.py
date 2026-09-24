"""Safe local report exports."""

from __future__ import annotations

import html
import re

from .models import InvestigationReport


def markdown(report: InvestigationReport) -> str:
    def esc(value: object) -> str:
        safe = html.escape(str(value), quote=True).replace("|", "&#124;")
        safe = re.sub(r"([\\`*_{}\[\]()#+.!>~-])", r"\\\1", safe)
        return safe.replace("\n", "<br>")

    lines = [
        f"# Investigation: {esc(report.title)}",
        "",
        f"Incident: {esc(report.incident_id)}  ",
        f"Generated: {esc(report.generated_at.isoformat())}  ",
        f"Mode: {esc(report.requested_mode)}; AI status: {esc(report.ai_status)}",
        "",
    ]
    if report.description:
        lines.extend([esc(report.description), ""])
    lines.extend(["## Observed findings", ""])
    for finding in report.findings:
        lines.extend([
            f"### {esc(finding.rule_id)} ({esc(finding.severity)})",
            "", esc(finding.statement), "",
            "Evidence: " + ", ".join(esc(i) for i in finding.evidence_ids), "",
        ])
        lines.extend(f"- Limitation: {esc(item)}" for item in finding.limitations)
        lines.extend(f"- Check: {esc(item)}" for item in finding.next_checks)
        lines.append("")
    lines.extend(["## Evidence limitations", ""])
    lines.extend(f"- {esc(item)}" for item in report.evidence_limitations)
    if not report.evidence_limitations:
        lines.append("- No additional rule limitations recorded; capture may still be incomplete.")
    lines.extend(["", "## Timeline and evidence", "",
                  "| UTC time | ID | Kind | Service | Message | Relationships |",
                  "| --- | --- | --- | --- | --- | --- |"])
    by_id = {r.id: r for r in report.evidence}
    for entry in report.timeline:
        record = by_id[entry.evidence_id]
        lines.append("| " + " | ".join(esc(part) for part in (
            entry.occurred_at_utc.isoformat(), record.id, record.kind.value,
            record.service, record.message, "; ".join(entry.relationships),
        )) + " |")
    lines.extend(["", "## AI hypotheses", "",
                  "No AI explanation requested." if report.ai_status == "not_requested"
                  else f"AI status: {esc(report.ai_status)}", ""])
    return "\n".join(lines)
