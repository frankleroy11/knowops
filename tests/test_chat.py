import json
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


def model_answer(claims=None, **kwargs):
    return {
        "answerable": True,
        "unanswered_questions": [],
        "claims": claims
        if claims is not None
        else [{"text": "先申请账号", "evidence": [{"source_id": 1, "quote": "先申请 VPN 账号"}]}],
        **kwargs,
    }


@pytest.mark.parametrize(
    "response,status",
    [
        (model_answer(answerable=False), "model_refused"),
        (model_answer(unanswered_questions=["缺少时限"]), "incomplete_answer"),
        (model_answer(claims=[]), "missing_claims"),
        (
            model_answer(
                claims=[
                    {
                        "text": "申请账号",
                        "evidence": [{"source_id": 99, "quote": "资料中不存在的证据"}],
                    }
                ]
            ),
            "invalid_source",
        ),
        (
            model_answer(
                claims=[
                    {"text": "申请账号", "evidence": [{"source_id": 1, "quote": "无需申请账号"}]}
                ]
            ),
            "invalid_evidence",
        ),
        (
            model_answer(
                claims=[{"text": "申请账号", "evidence": [{"source_id": 1, "quote": " "}]}]
            ),
            "invalid_evidence",
        ),
    ],
)
def test_unverified_answers_are_refused(response, status):
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response):
        result = answer_question(BODY, HITS)
    assert not result["answerable"]
    assert result["citations"] == []
    assert result["grounding_status"] == status


def test_multiple_facts_resolve_all_sources_and_assemble_answer():
    hits = HITS + [{"chunk_id": 6, "content": "有效期 2 小时", "filename": "time.md"}]
    claims = [
        {"text": "先申请账号", "evidence": [{"source_id": 1, "quote": "先申请 VPN 账号"}]},
        {
            "text": "有效期2小时",
            "evidence": [
                {"source_id": 2, "quote": "有效期 2 小时"},
                {"source_id": 2, "quote": "2 小时"},
            ],
        },
    ]
    with patch(
        "app.modules.chat.router.generate_grounded_answer", return_value=model_answer(claims)
    ):
        result = answer_question(BODY, hits)
    assert result["answer"] == "先申请账号\n有效期2小时"
    assert [c["chunk_id"] for c in result["citations"]] == [5, 6]
    assert result["grounding_status"] == "quotes_validated"


def test_quote_outside_model_context_is_rejected():
    hits = [{"content": "甲" * 1200 + "隐藏证据", "chunk_id": 5}]
    claims = [{"text": "事实", "evidence": [{"source_id": 1, "quote": "隐藏证据"}]}]
    with patch(
        "app.modules.chat.router.generate_grounded_answer", return_value=model_answer(claims)
    ):
        assert answer_question(BODY, hits)["grounding_status"] == "invalid_evidence"


def test_one_bad_claim_rejects_entire_answer():
    response = model_answer()
    response["claims"].append({"text": "两小时", "evidence": [{"source_id": 1, "quote": "两小时"}]})
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response):
        assert answer_question(BODY, HITS)["citations"] == []


def test_missing_evidence_schema_is_502():
    response = model_answer([{"text": "无依据事实", "evidence": []}])
    with (
        patch("app.modules.chat.router.generate_grounded_answer", return_value=response),
        pytest.raises(HTTPException) as error,
    ):
        answer_question(BODY, HITS)
    assert error.value.status_code == 502


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
        system = json.loads(request.content)["messages"][0]["content"]
        assert "合法source_id仅为[1]" in system
        assert "应回答不可以" in system
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(model_answer(), ensure_ascii=False)}}
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


def test_whitespace_layout_differences_are_allowed():
    hits = [{"content": "有效期\n 2 小时", "chunk_id": 7}]
    response = model_answer(
        [{"text": "有效期2小时", "evidence": [{"source_id": 1, "quote": "有效期 2 小时"}]}]
    )
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response):
        assert answer_question(BODY, hits)["answerable"] is True


def test_free_answer_outside_claims_is_rejected():
    response = {**model_answer(), "answer": "额外无依据建议"}
    with (
        patch("app.modules.chat.router.generate_grounded_answer", return_value=response),
        pytest.raises(HTTPException) as error,
    ):
        answer_question(BODY, HITS)
    assert error.value.status_code == 502


def test_real_wrong_id_regression_resolves_only_unique_exact_quotes():
    from app.core.config import ROOT

    diagnostic = json.loads((ROOT / "evals/citation_runs/source-id-diagnostic.json").read_text())
    original = json.loads((ROOT / diagnostic["context_source"]).read_text())
    row = next(r for r in original["rows"] if r["id"] == "NEW-03" and r["strategy"] == "dense_3")
    with patch(
        "app.modules.chat.router.generate_grounded_answer",
        return_value=diagnostic["raw_generation"],
    ):
        result = answer_question(BODY, row["selected_hits"])
    assert result["answerable"] is True
    assert result["source_id_corrections"] == [
        {"claim_index": 0, "model_source_id": 5, "source_id": 1},
        {"claim_index": 0, "model_source_id": 12, "source_id": 3},
    ]
    assert [c["source_id"] for c in result["citations"]] == [2, 1, 3]
    assert [c["chunk_id"] for c in result["citations"]] == [
        row["selected_hits"][i - 1]["chunk_id"] for i in [2, 1, 3]
    ]


def test_ambiguous_quote_does_not_repair_invalid_id():
    hits = HITS + [{**HITS[0], "chunk_id": 6}]
    response = model_answer(
        [{"text": "申请账号", "evidence": [{"source_id": 99, "quote": "先申请 VPN 账号"}]}]
    )
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response):
        result = answer_question(BODY, hits)
    assert result["grounding_status"] == "invalid_source"
    assert result["citations"] == []


def test_correct_id_with_repeated_quote_is_preserved():
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=model_answer()):
        result = answer_question(BODY, HITS + [{**HITS[0], "chunk_id": 6}])
    assert result["answerable"]
    assert result["source_id_corrections"] == []
    assert [c["chunk_id"] for c in result["citations"]] == [5]


def test_in_range_wrong_source_can_only_repair_unique_quote():
    hits = HITS + [{"content": "有效期 2 小时", "chunk_id": 6}]
    response = model_answer(
        [{"text": "有效期2小时", "evidence": [{"source_id": 1, "quote": "有效期 2 小时"}]}]
    )
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response):
        result = answer_question(BODY, hits)
    assert [c["chunk_id"] for c in result["citations"]] == [6]
    assert result["source_id_corrections"] == [
        {"claim_index": 0, "model_source_id": 1, "source_id": 2}
    ]


def test_neighbor_mode_can_cite_context_beyond_retrieval_top_k():
    hits = HITS + [
        {
            "chunk_id": 6,
            "content": "具体额度2天",
            "filename": "quota.md",
            "knowledge_base_name": "制度库",
        }
    ]
    response = model_answer(
        [{"text": "额度2天", "evidence": [{"source_id": 2, "quote": "具体额度2天"}]}]
    )
    body = AskRequest(question="额度几天", knowledge_base_id=2, top_k=1, expand_context=True)
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response) as model:
        result = answer_question(body, hits)
    assert result["citations"][0]["chunk_id"] == 6
    assert model.call_args.args[1][1]["filename"] == "quota.md"
    assert model.call_args.args[1][1]["knowledge_base"] == "制度库"
    with patch("app.modules.chat.router.generate_grounded_answer", return_value=response):
        result = answer_question(
            AskRequest(question="额度几天", knowledge_base_id=2, top_k=1), hits
        )
    assert not result["answerable"]


@pytest.mark.parametrize("enabled", [False, True])
def test_ask_routes_optional_neighbor_context(enabled):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.modules.chat import router as chat
    from app.modules.knowledge.router import get_db

    anchors = HITS
    expanded = HITS + [{"content": "补充资料", "chunk_id": 6}]
    app.dependency_overrides[get_db] = lambda: None
    try:
        with (
            patch.object(chat, "search", return_value={"hits": anchors}),
            patch.object(chat, "expand_neighbors", return_value=expanded) as expand,
            patch.object(
                chat,
                "answer_question",
                return_value={"answer": "资料不足", "answerable": False, "citations": []},
            ) as answer,
        ):
            response = TestClient(app).post(
                "/api/v1/chat/ask",
                json={"question": "VPN", "scope": "all", "expand_context": enabled},
            )
        assert response.status_code == 200
        assert response.json()["context_expanded"] is enabled
        assert response.json()["context_chunk_count"] == (2 if enabled else 1)
        assert answer.call_args.args[1] == (expanded if enabled else anchors)
        if enabled:
            expand.assert_called_once_with(anchors, None)
        else:
            expand.assert_not_called()
    finally:
        app.dependency_overrides.clear()
