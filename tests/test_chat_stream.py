import asyncio
import json
from contextlib import nullcontext
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from app.adapters.llm import qwen
from app.core.config import Settings
from app.modules.chat.router import AskRequest, stream_ask


def collect(answer=None, error=None):
    async def run():
        with (
            patch('app.db.session.SessionLocal', return_value=nullcontext(None)),
            patch('app.modules.chat.router.ask', return_value=answer, side_effect=error),
        ):
            response = await stream_ask(AskRequest(question='测试', scope='all'), None)
            return ''.join([item async for item in response.body_iterator])
    return asyncio.run(run())


def test_validated_result_and_terminal_event():
    result = {'answer': '已验证的答案' * 10, 'citations': [], 'answerable': True}
    output = collect(result)
    assert output.index('event: status') < output.index('event: delta')
    assert output.count('event: done') == 1
    frames = output.split('\n\n')
    deltas = [json.loads(f.split('data: ')[1])['text'] for f in frames
              if f.startswith('event: delta')]
    assert ''.join(deltas) == result['answer']


def test_error_does_not_emit_answer():
    output = collect(error=HTTPException(503, '模型暂不可用'))
    assert 'event: error' in output
    assert 'event: delta' not in output
    assert 'event: done' not in output


@pytest.mark.parametrize('complete', [True, False])
def test_provider_stream_and_truncation(complete):
    settings = Settings(llm_model='test', llm_base_url='http://model/v1')
    answer = json.dumps({'answerable': False, 'claims': [], 'unanswered_questions': []})
    data = 'data: ' + json.dumps({'choices': [{'delta': {'content': answer}}]}) + '\n\n'
    if complete:
        data += 'data: [DONE]\n\n'
    def handler(request):
        assert json.loads(request.content)['stream'] is True
        return httpx.Response(200, text=data)
    original = httpx.Client
    counts = []
    marker = qwen.STREAM_PROGRESS.set(counts.append)
    try:
        with (
            patch.object(qwen, 'get_settings', return_value=settings),
            patch.object(qwen.httpx, 'Client', side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handler), **kw)),
        ):
            if complete:
                assert qwen.generate_grounded_answer('测试', [])['answerable'] is False
                assert counts == [len(answer)]
            else:
                with pytest.raises(qwen.LLMUnavailable):
                    qwen.generate_grounded_answer('测试', [])
    finally:
        qwen.STREAM_PROGRESS.reset(marker)
