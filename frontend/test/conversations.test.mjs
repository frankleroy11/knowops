import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import {
  MAX_MESSAGES_PER_SCOPE,
  STORAGE_KEY,
  createConversationPersistence,
  createConversationStore,
  parseConversations,
  scopeKey,
  snapshotConversations,
  switchScope,
  trimMessage,
} from '../src/conversations.js'

const answer = (text) => ({ role: 'assistant', text })

test('scopeKey separates the unified scope from each knowledge base', () => {
  assert.equal(scopeKey('all'), 'all')
  assert.equal(scopeKey(7), '7')
  assert.equal(scopeKey('7'), '7')
  assert.notEqual(scopeKey('all'), scopeKey(1))
})

test('switching to another knowledge base and back keeps the conversation', () => {
  const store = createConversationStore()
  const unified = { messages: [{ role: 'user', text: 'VPN 怎么申请？' }, answer('先提交申请单。')], question: '' }

  // 在统一问答提问后切到知识库 1：先把统一问答存起来，知识库 1 还是空的
  store.stash(scopeKey('all'), unified)
  assert.equal(store.restore(scopeKey(1)), null)

  // 在知识库 1 提问后切回统一问答：知识库 1 自己的记录也要留住
  const kb1 = { messages: [{ role: 'user', text: '年假几天？' }, answer('5 天。')] , question: '草稿' }
  store.stash(scopeKey(1), kb1)

  assert.deepEqual(store.restore(scopeKey('all')), unified)
  assert.deepEqual(store.restore(scopeKey(1)), kb1)
  assert.equal(store.size(), 2)
})

test('stashed buckets keep the live array so later answers land in the same record', () => {
  const store = createConversationStore()
  const conversation = { messages: [], question: '' }
  store.stash('all', conversation)
  store.restore('all').messages.push(answer('后到的回答'))
  assert.equal(conversation.messages.length, 1)
})

test('clearing removes every scope so a new login sees nothing', () => {
  const store = createConversationStore()
  store.stash('all', { messages: [answer('a')], question: '' })
  store.stash(1, { messages: [answer('b')], question: '' })
  store.clear()
  assert.equal(store.size(), 0)
  assert.equal(store.restore('all'), null)
  assert.equal(store.restore(1), null)
})

test('an empty key is ignored instead of creating a bucket', () => {
  const store = createConversationStore()
  store.stash('', { messages: [] })
  assert.equal(store.size(), 0)
})

test('reported bug: ask in unified, switch to a KB, come back and the answer is still there', () => {
  const store = createConversationStore()
  let messages = [{ role: 'user', text: 'VPN 怎么申请？' }, answer('先提交申请单。')]
  let question = ''

  // 切到知识库 1
  let state = switchScope(store, { from: scopeKey('all'), to: scopeKey(1), messages, question })
  assert.deepEqual(state.messages, [])
  messages = state.messages
  question = state.question

  // 在知识库 1 里提问
  messages.push({ role: 'user', text: '年假几天？' }, answer('5 天。'))

  // 切回统一问答：之前那条回答必须还在
  state = switchScope(store, { from: scopeKey(1), to: scopeKey('all'), messages, question })
  assert.deepEqual(state.messages.map((m) => m.text), ['VPN 怎么申请？', '先提交申请单。'])

  // 再切回知识库 1：那边的记录也在
  state = switchScope(store, { from: scopeKey('all'), to: scopeKey(1), messages: state.messages, question: '' })
  assert.deepEqual(state.messages.map((m) => m.text), ['年假几天？', '5 天。'])
})

test('an answer that arrives after switching scopes lands in the scope it was asked in', () => {
  const store = createConversationStore()
  const unified = { messages: [{ role: 'user', text: 'q-all' }], question: '' }
  const state = switchScope(store, { from: scopeKey('all'), to: scopeKey(2), messages: unified.messages, question: '' })
  // 请求已发出但用户切走了：迟到的回答 push 进的是统一问答那一桶
  store.restore(scopeKey('all')).messages.push(answer('迟到的回答'))
  assert.deepEqual(store.restore(scopeKey('all')).messages.map((m) => m.text), ['q-all', '迟到的回答'])
  assert.deepEqual(state.messages, [])
})

test('the unsent question draft survives a scope round trip', () => {
  const store = createConversationStore()
  // 在统一问答里输入了还没发送的问题，切到知识库 3
  const entering = switchScope(store, { from: scopeKey('all'), to: scopeKey(3), messages: [], question: '未发完的问题' })
  assert.equal(entering.question, '')
  // 切回来时草稿还在，不会白打一遍
  const back = switchScope(store, { from: scopeKey(3), to: scopeKey('all'), messages: entering.messages, question: '草稿3' })
  assert.equal(back.question, '未发完的问题')
})

test('App.vue routes the scope switch through switchScope instead of clearing messages', () => {
  const source = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
  const watcher = source.slice(source.indexOf('watch(selected'), source.indexOf('async function create'))
  assert.match(watcher, /switchScope\(conversations/)
  assert.match(watcher, /messages\.value = conversation\.messages/)
  assert.doesNotMatch(watcher, /messages\.value = \[\]/)
})

// ---- 持久化（刷新页面后仍在）----

class FakeStorage {
  constructor(limit = Infinity) {
    this.limit = limit
    this.data = new Map()
  }
  getItem(key) {
    return this.data.has(key) ? this.data.get(key) : null
  }
  setItem(key, value) {
    if (value.length > this.limit) throw new Error('QuotaExceededError')
    this.data.set(key, value)
  }
  removeItem(key) {
    this.data.delete(key)
  }
}

test('a saved conversation survives a reload', () => {
  const storage = new FakeStorage()
  const persistence = createConversationPersistence(storage)
  const store = createConversationStore()
  store.stash('all', { messages: [{ role: 'user', text: 'q' }, answer('a')], question: '草稿' })
  assert.equal(persistence.save(store.entries()), true)

  // 新页面：全新 store + 从 storage 恢复
  const reloaded = createConversationStore()
  reloaded.load(persistence.load())
  const restored = reloaded.restore('all')
  assert.deepEqual(restored.messages.map((m) => m.text), ['q', 'a'])
  assert.equal(restored.question, '草稿')
})

test('long citation text is truncated before saving', () => {
  const long = 'x'.repeat(2000)
  const trimmed = trimMessage({ role: 'assistant', citations: [{ content: long }, { content: 'short' }] })
  assert.equal(trimmed.citations[0].content.length, 600)
  assert.equal(trimmed.citations[1].content, 'short')
  assert.equal(trimMessage({ role: 'user', text: 'no citations' }).text, 'no citations')
})

test('only the most recent messages per scope are kept', () => {
  const messages = Array.from({ length: MAX_MESSAGES_PER_SCOPE + 5 }, (_, i) => answer(`m${i}`))
  const snapshot = snapshotConversations([['all', { messages, question: '' }]])
  const kept = snapshot[0][1].messages
  assert.equal(kept.length, MAX_MESSAGES_PER_SCOPE)
  assert.equal(kept[0].text, 'm5')
})

test('when the quota is exceeded the oldest scopes are dropped first', () => {
  const store = createConversationStore()
  const big = 'y'.repeat(500)
  for (const key of ['all', '1', '2']) {
    store.stash(key, { messages: [answer(big)], question: '' })
  }
  // 配额只够装下最近的一份（用真实序列化长度算阈值，避免拍脑袋）
  const oneEntry = JSON.stringify(snapshotConversations([['2', { messages: [answer(big)], question: '' }]]))
  const persistence = createConversationPersistence(new FakeStorage(oneEntry.length + 10))
  assert.equal(persistence.save(store.entries()), true)
  const restored = createConversationStore()
  restored.load(persistence.load())
  assert.equal(restored.has('all'), false)
  assert.equal(restored.has('1'), false)
  assert.equal(restored.has('2'), true)
})

test('a storage that always fails degrades gracefully', () => {
  const broken = {
    getItem() { throw new Error('blocked') },
    setItem() { throw new Error('blocked') },
    removeItem() { throw new Error('blocked') },
  }
  const store = createConversationStore()
  store.stash('all', { messages: [answer('a')], question: '' })
  const persistence = createConversationPersistence(broken)
  assert.deepEqual(persistence.load(), [])
  assert.equal(persistence.save(store.entries()), false)
  persistence.clear()
})

test('garbage in storage never breaks the page', () => {
  assert.deepEqual(parseConversations(null), [])
  assert.deepEqual(parseConversations(''), [])
  assert.deepEqual(parseConversations('not json'), [])
  assert.deepEqual(parseConversations('{"a":1}'), [])
  assert.deepEqual(parseConversations('[["all"]]'), [])
  assert.deepEqual(parseConversations('[[1,{}]]'), [])
  const partial = parseConversations('[["all",{"messages":"nope"}]]')
  assert.deepEqual(partial, [['all', { messages: [], question: '' }]])
})

test('no storage means no persistence but the app still works', () => {
  const persistence = createConversationPersistence(null)
  assert.deepEqual(persistence.load(), [])
  assert.equal(persistence.save([['all', { messages: [], question: '' }]]), false)
  persistence.clear()
  assert.equal(STORAGE_KEY, 'knowops.conversations')
})
