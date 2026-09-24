# Backlog

Statuses: `planned`, `in_progress`, `blocked`, `ready_for_review`, `merged`. Each task starts after its dependency is merged into `main`.

| ID | Outcome and acceptance criteria | Depends on | Status |
| --- | --- | --- | --- |
| INV-001 | Versioned JSON/JSONL contract, bounded ingestion, redaction, correlation, rules R1-R3, five cases, generated schemas and CLI tests. Offline rules command generates accurate evidence-linked JSON and Markdown. | None | merged |
| INV-002 | Anthropic adapter, versioned prompt, bounded context, evidence/output validation and fallback. Mocked success, missing key, timeout, transient failure, malformed output, bad references and injection case pass; live status is honest. | INV-001 merged | merged |
| INV-003 | FastAPI and static browser UI for upload, validation, rules, explicit AI request, evidence navigation and exports. Manually verify browser workflow or state tooling limit. | INV-002 merged | merged |
| INV-004 | .NET and Python exporters, 15-case split corpus, offline evaluation and comparison runner. Cross-language findings match and offline evaluation reproduces. | INV-003 merged | merged |
| INV-005 | Setup and learning documentation, walkthrough, CI and packaging checks. Native commands and required offline checks pass. | INV-004 merged | ready_for_review |
