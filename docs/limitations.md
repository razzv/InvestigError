# Limitations and boundaries

- Findings describe supplied records and declared invariants. Export gaps, missing downstream logs and cross-service clock differences limit conclusions. A 2xx delivery acknowledgement does not prove processing completed.
- R1 and R2 need explicit invariants. Repeated delivery alone is not a duplicate committed effect; two log lines about one effect are not two commits.
- Redaction recognizes known patterns and aliases selected identifiers, but is best-effort. Inspect input, the browser's exact provider-context preview and reports before sharing or enabling cloud transmission.
- AI explanation is optional. It requires an explicit model, credentials and cloud consent. The response schema and evidence IDs are checked, but cited evidence may not actually support a model's claim. Provider failures leave the deterministic report available.
- The 18-case corpus is synthetic. Its previously inspected holdout split now serves as regression coverage. Offline quality-gate results measure behavior on those cases, not production accuracy. Live model quality, usefulness, latency, token use and cost remain unmeasured until actual calls and human review occur.
- The browser service is for one local user on loopback. It has no authentication, shared storage or public-hosting security design. Accepted uploads are held in bounded memory; reports downloaded from the browser are not saved by the server.
- The .NET and Python exporters are synthetic demonstrations. They do not connect to a payment provider or prove production integration behavior.

See the [evaluation protocol](evaluation.md) for what is scored and the [incident contract](incident-format.md) for input limits.
