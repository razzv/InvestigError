"""Local browser-test server with synthetic provider output; never calls a live model."""

from __future__ import annotations

import json
import os

import uvicorn

from investigerror import explanation
from investigerror.providers.base import ProviderResult


class MockProvider:
    def explain(self, context: str, system_prompt: str, schema: dict[str, object]) -> ProviderResult:
        payload = {
            "summary": "Synthetic provider summary.",
            "hypotheses": [{
                "category": "other",
                "statement": "<img src=x onerror=alert(1)> Uncited possibility.",
                "evidence_ids": [],
                "reasoning_summary": "Reasoning needs a missing trace.",
                "missing_evidence": ["Missing worker trace M-17."],
                "verification_steps": ["Inspect worker M-17."],
            }],
            "alternatives": [{
                "statement": "Alternative branch.",
                "evidence_ids": ["a2"],
                "missing_evidence": ["Missing retry log A-2."],
            }],
            "next_steps": ["Inspect the local queue."],
            "limitations": ["AI limitation L-9: capture is partial."],
        }
        return ProviderResult(json.dumps(payload), "synthetic-browser-test", "end_turn", 1, 12, 25)


explanation.AnthropicProvider = lambda *args: MockProvider()  # type: ignore[assignment]
os.environ["ANTHROPIC_API_KEY"] = "synthetic-browser-test-key"
os.environ["AI_MODEL"] = "synthetic-browser-test"
uvicorn.run("investigerror.api:app", host="127.0.0.1", port=int(os.environ["INV_BROWSER_TEST_PORT"]))
