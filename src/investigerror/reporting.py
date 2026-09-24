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
    lines.extend(["", "## AI explanation", ""])
    if report.ai_explanation:
        explanation = report.ai_explanation
        lines.extend([esc(explanation.summary), "", "### Hypotheses", ""])
        for item in explanation.hypotheses:
            lines.extend([
                f"- {esc(item.category)}: {esc(item.statement)}",
                f"  - Evidence: {', '.join(esc(eid) for eid in item.evidence_ids) or 'none cited'}",
                f"  - Reasoning summary: {esc(item.reasoning_summary)}",
            ])
            lines.extend(f"  - Missing evidence: {esc(value)}" for value in item.missing_evidence)
            lines.extend(f"  - Verify: {esc(value)}" for value in item.verification_steps)
        lines.extend(["", "### Alternatives", ""])
        for alternative in explanation.alternatives:
            lines.append(f"- {esc(alternative.statement)}")
            lines.append(f"  - Evidence: {', '.join(esc(eid) for eid in alternative.evidence_ids) or 'none cited'}")
            lines.extend(f"  - Missing evidence: {esc(value)}" for value in alternative.missing_evidence)
        lines.extend(["", "### Next steps", ""])
        lines.extend(f"{index}. {esc(step)}" for index, step in enumerate(explanation.next_steps, 1))
        lines.extend(["", "### AI limitations", ""])
        lines.extend(f"- {esc(value)}" for value in explanation.limitations)
    elif report.ai_status == "not_requested":
        lines.append("No AI explanation requested.")
    else:
        lines.append(f"AI status: {esc(report.ai_status)}. The rules report remains available.")
    lines.extend([
        "", "## Context coverage", "",
        f"Selected records: {report.metadata.selected_record_count}; "
        f"omitted records: {report.metadata.omitted_record_count}.",
        "", "## Warnings", "",
    ])
    lines.extend(f"- {esc(item)}" for item in report.metadata.warnings)
    lines.append("")
    return "\n".join(lines)
