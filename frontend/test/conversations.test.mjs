import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { createConversationStore, scopeKey, switchScope } from '../src/conversations.js'

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
