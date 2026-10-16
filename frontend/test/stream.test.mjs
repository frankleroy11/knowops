import test from 'node:test'
import assert from 'node:assert/strict'
import {readAnswerStream} from '../src/stream.js'
const encoder = new TextEncoder()
function bytes(text) {
  return new ReadableStream({start(controller) {
    for (const byte of encoder.encode(text)) controller.enqueue(Uint8Array.of(byte))
    controller.close()
  }})
}
test('SSE preserves Chinese and CRLF across single byte chunks', async () => {
  const events = []
  await readAnswerStream(bytes('event: delta\r\ndata: {"text":"中文"}\r\n\r\nevent: done\ndata: {"answer":"中文"}\n\n'), (type, data) => events.push([type, data]))
  assert.deepEqual(events, [['delta', {text:'中文'}], ['done', {answer:'中文'}]])
})
test('truncated stream is rejected', async () => {
  await assert.rejects(readAnswerStream(bytes('event: delta\ndata: {"text":"部分"}\n\n'), () => {}), /未完成/)
})
test('server error is shown and never treated as completed', async () => {
  await assert.rejects(readAnswerStream(bytes('event: error\ndata: {"message":"不可用"}\n\n'), () => {}), /不可用/)
})
