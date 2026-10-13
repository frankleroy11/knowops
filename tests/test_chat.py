from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from app.adapters.llm.qwen import LLMUnavailable, generate_grounded_answer
from app.core.config import Settings
from app.modules.chat.router import AskRequest, answer_question

BODY = AskRequest(question="如何连接 VPN？", knowledge_base_id=2)
HITS = [{"chunk_id": 5, "content": "先申请 VPN 账号", "filename": "vpn.md", "page": None}]


def test_no_context_does_not_call_llm():
    with patch("app.modules.chat.router.generate_grounded_answer") as model:
        assert answer_question(BODY, [])["answerable"] is False
        model.assert_not_called()


@pytest.mark.parametrize("ids,answerable", [([99], True), ([], True), ([1], False)])
def test_refusal_and_fabricated_source(ids, answerable):
    with patch(
        "app.modules.chat.router.generate_grounded_answer",
        return_value={"answer": "内容", "source_ids": ids, "answerable": answerable},
    ):
        result = answer_question(BODY, HITS)
        assert result["answerable"] is False
        assert result["citations"] == []


def test_citations_are_resolved_from_backend():
    with patch(
        "app.modules.chat.router.generate_grounded_answer",
        return_value={"answer": "申请账号", "source_ids": [1, 1], "answerable": True},
    ):
        result = answer_question(BODY, HITS)
        assert len(result["citations"]) == 1
        assert result["citations"][0]["chunk_id"] == 5


def test_provider_failure_is_503():
    with patch(
        "app.modules.chat.router.generate_grounded_answer", side_effect=LLMUnavailable("不可用")
    ):
        with pytest.raises(HTTPException) as error:
            answer_question(BODY, HITS)
        assert error.value.status_code == 503


def test_adapter_http_contract():
    def handler(request):
        assert request.url.path == "/compatible-mode/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"answer":"申请账号","source_ids":[1],"answerable":true}'
                        }
                    }
                ]
            },
        )

    original = httpx.Client
    with (
        patch(
            "app.adapters.llm.qwen.get_settings",
            return_value=Settings(
                llm_model="qwen-plus",
                llm_base_url="https://example.org/compatible-mode/v1",
                llm_api_key="test-key",
            ),
        ),
        patch(
            "app.adapters.llm.qwen.httpx.Client",
            side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
        ),
    ):
        assert generate_grounded_answer("VPN", [{"id": 1, "content": "申请账号"}])["answerable"]
