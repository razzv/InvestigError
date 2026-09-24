from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from investigerror.providers.anthropic import AnthropicProvider
from investigerror.providers.base import ProviderFailure


class FakeMessages:
    def __init__(self, response: object = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def test_adapter_uses_structured_request_timeout_and_one_sdk_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"summary":"ok"}')],
        model="test-model", stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=8, output_tokens=4),
    )
    messages = FakeMessages(response=response)
    constructor: list[dict[str, object]] = []

    def fake_client(**kwargs: object) -> object:
        constructor.append(kwargs)
        return SimpleNamespace(messages=messages)

    monkeypatch.setattr(anthropic, "Anthropic", fake_client)
    adapter = AnthropicProvider("synthetic-test-key", "test-model", 7.5, 3000)
    result = adapter.explain('{"records":[]}', "System instructions", {
        "type": "object", "properties": {"summary": {"type": "string"}},
        "required": ["summary"], "additionalProperties": False,
    })
    assert constructor == [{"api_key": "synthetic-test-key", "timeout": 7.5, "max_retries": 1}]
    assert len(messages.calls) == 1
    call = messages.calls[0]
    assert call["max_tokens"] == 3000
    assert call["model"] == "test-model"
    assert call["messages"] == [{"role": "user", "content": '{"records":[]}'}]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert result.text == '{"summary":"ok"}'
    assert (result.input_tokens, result.output_tokens) == (8, 4)


@pytest.mark.parametrize("kind", ["timeout", "rate_limit"])
def test_adapter_maps_transient_sdk_errors_without_raw_response(
    monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    if kind == "timeout":
        error = anthropic.APITimeoutError(request)
    else:
        error = anthropic.RateLimitError(
            "token=synthetic-response-secret",
            response=httpx2.Response(429, request=request), body=None,
        )
    messages = FakeMessages(error=error)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **_: SimpleNamespace(messages=messages))
    adapter = AnthropicProvider("synthetic-test-key", "test-model", 7.5, 3000)
    with pytest.raises(ProviderFailure) as caught:
        adapter.explain("{}", "prompt", {"type": "object", "properties": {}})
    assert "synthetic-response-secret" not in str(caught.value)
    assert len(messages.calls) == 1
