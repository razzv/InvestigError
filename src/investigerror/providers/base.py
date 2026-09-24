"""Small provider contract, independent of SDK response classes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResult:
    text: str
    model: str
    stop_reason: str | None
    duration_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderFailure(Exception):
    """A provider request failed without exposing request or credential contents."""


class ExplanationProvider(Protocol):
    def explain(self, context: str, system_prompt: str, schema: dict[str, Any]) -> ProviderResult: ...
