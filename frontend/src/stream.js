/** 增量解码 SSE：兼容 UTF-8 跨块、CRLF 与分隔符跨块，结束事件不可缺失。 */
export async function readAnswerStream(body, onEvent) {
  const reader = body.getReader(), decoder = new TextDecoder()
  let buffer = '', done = false
  const dispatch = frame => {
    const lines = frame.split('\n')
    const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
    const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
    if (!event || !data) return
    const payload = JSON.parse(data)
    if (event === 'error') throw new Error(payload.message || '流式问答失败')
    onEvent(event, payload)
    if (event === 'done') done = true
  }
  try {
    while (!done) {
      const result = await reader.read()
      buffer += decoder.decode(result.value, {stream: !result.done})
      buffer = buffer.replace(/\r\n/g, '\n')
      let boundary
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        dispatch(buffer.slice(0, boundary)); buffer = buffer.slice(boundary + 2)
        if (done) break
      }
      if (result.done) break
    }
    if (!done) throw new Error('连接中断，答案未完成，请重试')
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock() }
}
