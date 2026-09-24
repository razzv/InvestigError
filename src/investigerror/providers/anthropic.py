"""One structured Anthropic Messages request with bounded SDK retry behavior."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import anthropic

from .base import ProviderFailure, ProviderResult


class AnthropicProvider:
    def __init__(self, api_key: str, model: str, timeout_seconds: float, max_output_tokens: int):
        self.model = model
        self.max_output_tokens = max_output_tokens
        # The SDK performs at most one retry for its documented transient failures.
        self.client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=1,
        )

    def explain(self, context: str, system_prompt: str, schema: dict[str, Any]) -> ProviderResult:
        started = perf_counter()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": context}],
                output_config={
                    "format": {"type": "json_schema", "schema": anthropic.transform_schema(schema)}
                },
            )
        except anthropic.APITimeoutError as exc:
            raise ProviderFailure("Anthropic request timed out.") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderFailure("Anthropic connection failed.") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderFailure("Anthropic rate limit or spend limit was reached.") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderFailure(f"Anthropic returned HTTP {exc.status_code}.") from exc
        except anthropic.APIError as exc:
            raise ProviderFailure("Anthropic request failed.") from exc
        blocks = [block.text for block in response.content if block.type == "text"]
        return ProviderResult(
            text="".join(blocks),
            model=response.model,
            stop_reason=response.stop_reason,
            duration_ms=round((perf_counter() - started) * 1000),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
