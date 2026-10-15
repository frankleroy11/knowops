"""LangChain 编排回归：真实 Runnable 与 HTTP 模拟，禁止外部模型调用。"""

import json
from unittest.mock import patch

import httpx
import pytest
from langsmith import get_tracing_context

from app.adapters.llm import qwen
from app.core.config import Settings

SETTINGS = Settings(
    llm_model="qwen-test",
    llm_base_url="https://example.org/v1/",
    llm_api_key="private-test-key",
)


def run_response(response, *, question="费用 {amount}", sources=None):
    requests = []

    def handler(request):
        requests.append(request)
        assert get_tracing_context()["enabled"] is False
        return (
            response(request)
            if callable(response)
            else httpx.Response(200, json={"choices": [{"message": {"content": response}}]})
        )

    original = httpx.Client
    with (
        patch.object(qwen, "get_settings", return_value=SETTINGS),
        patch.object(
            qwen.httpx,
            "Client",
            side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
        ),
    ):
        result = qwen.generate_grounded_answer(
            question,
            sources if sources is not None else [{"id": 9, "content": '原文 {"x": 1}'}],
        )
    return result, requests


def test_chain_keeps_literal_evidence_and_nonsequential_ids():
    answer = {"answerable": False, "claims": [], "unanswered_questions": ["费用"]}
    result, requests = run_response("```json\n" + json.dumps(answer) + "\n```")
    assert result == answer
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert "合法source_id仅为[9]" in body["messages"][0]["content"]
    data = json.loads(body["messages"][1]["content"])
    assert data == {"question": "费用 {amount}", "sources": [{"id": 9, "content": '原文 {"x": 1}'}]}
    assert body["temperature"] == 0
    assert body["stream"] is False
    assert body["max_tokens"] == 1200


@pytest.mark.parametrize("content", ['{"answerable": true', "[]", "null", "不是 JSON", None])
def test_invalid_model_output_fails_closed(content):
    with pytest.raises(qwen.LLMUnavailable):
        run_response(content)


def test_provider_error_is_sanitized_and_not_retried():
    calls = []

    def failed(request):
        calls.append(request)
        return httpx.Response(429, text="private-test-key provider-debug-body")

    with pytest.raises(qwen.LLMUnavailable) as error:
        run_response(failed)
    assert len(calls) == 1
    assert "private-test-key" not in str(error.value)
    assert "provider-debug-body" not in str(error.value)


def test_missing_configuration_never_invokes_chain():
    with (
        patch.object(qwen, "get_settings", return_value=Settings(llm_model="", llm_base_url="")),
        patch.object(qwen, "ANSWER_CHAIN") as chain,
        pytest.raises(qwen.LLMUnavailable),
    ):
        qwen.generate_grounded_answer("问题", [])
    chain.invoke.assert_not_called()
