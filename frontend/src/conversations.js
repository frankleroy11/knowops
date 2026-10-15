/**
 * 问答记录按“检索范围”分别保留：统一问答（all）与每个知识库各一份。
 *
 * 组件里切换范围时调用 switchScope；本模块同时负责**序列化/反序列化**，
 * 让记录能落到 sessionStorage，刷新页面后仍在（关闭标签页即清空，避免共享机器上残留）。
 *
 * 纯逻辑、不依赖 Vue 与浏览器全局对象，便于用 `node --test` 直接测试。
 */

export const STORAGE_KEY = 'knowops.conversations'
export const MAX_MESSAGES_PER_SCOPE = 40
export const MAX_SCOPES = 20
export const MAX_CITATION_CHARS = 600
export const MAX_DRAFT_CHARS = 2000

export function scopeKey(selected) {
  return selected === 'all' ? 'all' : String(selected)
}

export function createConversationStore() {
  const buckets = new Map()
  return {
    /** 保存某个范围的问答记录；再次保存同一范围会把它移到“最近使用”的位置。 */
    stash(key, conversation) {
      if (!key) return
      buckets.delete(key)
      buckets.set(key, conversation)
    },
    restore(key) {
      return buckets.get(key) ?? null
    },
    has(key) {
      return buckets.has(key)
    },
    size() {
      return buckets.size
    },
    /** 按“最近使用”顺序导出，供持久化使用。 */
    entries() {
      return [...buckets.entries()]
    },
    /** 从持久化数据恢复（不覆盖已有内容）。 */
    load(entries) {
      for (const [key, conversation] of entries || []) {
        if (!buckets.has(key)) buckets.set(key, conversation)
      }
    },
    remove(key) {
      buckets.delete(key)
    },
    clear() {
      buckets.clear()
    },
  }
}

/**
 * 执行一次检索范围切换：先保存离开范围的问答记录，再返回进入范围的记录。
 * 这是组件里 watch(selected) 的那一步，抽出来便于测试。
 */
export function switchScope(store, { from, to, messages, question }) {
  store.stash(from, { messages, question })
  const saved = store.restore(to)
  return saved
    ? { messages: saved.messages, question: saved.question ?? '' }
    : { messages: [], question: '' }
}

/** 引用正文可能很长，持久化前截断，避免撑爆 sessionStorage。 */
export function trimMessage(message) {
  if (!message || !Array.isArray(message.citations)) return message
  return {
    ...message,
    citations: message.citations.map((citation) =>
      typeof citation?.content === 'string' && citation.content.length > MAX_CITATION_CHARS
        ? { ...citation, content: citation.content.slice(0, MAX_CITATION_CHARS) }
        : citation,
    ),
  }
}

/** 生成可序列化的快照：只保留最近的范围与消息条数。 */
export function snapshotConversations(entries) {
  return (entries || []).slice(-MAX_SCOPES).map(([key, conversation]) => [
    key,
    {
      question: String(conversation?.question ?? '').slice(0, MAX_DRAFT_CHARS),
      messages: (conversation?.messages || []).slice(-MAX_MESSAGES_PER_SCOPE).map(trimMessage),
    },
  ])
}

/** 解析持久化内容；任何脏数据都退化成空，不让页面挂掉。 */
export function parseConversations(raw) {
  if (typeof raw !== 'string' || !raw) return []
  let payload
  try {
    payload = JSON.parse(raw)
  } catch {
    return []
  }
  if (!Array.isArray(payload)) return []
  return payload
    .filter(
      (entry) =>
        Array.isArray(entry) &&
        entry.length === 2 &&
        typeof entry[0] === 'string' &&
        entry[0] &&
        entry[1] &&
        typeof entry[1] === 'object',
    )
    .map(([key, value]) => [
      key,
      {
        messages: Array.isArray(value.messages) ? value.messages : [],
        question: typeof value.question === 'string' ? value.question : '',
      },
    ])
}

/**
 * 会话持久化：默认写 sessionStorage；配额不足时先丢最旧的范围再试。
 * `storage` 传 null 时整体退化为内存（不持久化），便于测试与隐私模式。
 */
export function createConversationPersistence(storage) {
  if (!storage) {
    return { load: () => [], save: () => false, clear: () => {} }
  }
  return {
    load() {
      try {
        return parseConversations(storage.getItem(STORAGE_KEY))
      } catch {
        return []
      }
    },
    save(entries) {
      let snapshot = snapshotConversations(entries)
      while (true) {
        try {
          storage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
          return true
        } catch {
          if (snapshot.length <= 1) break
          snapshot = snapshot.slice(1) // 配额不足：丢掉最旧的范围
        }
      }
      try {
        storage.removeItem(STORAGE_KEY)
      } catch {
        /* 存储不可用时忽略 */
      }
      return false
    },
    clear() {
      try {
        storage.removeItem(STORAGE_KEY)
      } catch {
        /* 存储不可用时忽略 */
      }
    },
  }
}

/** Deleted knowledge must not survive as a restorable per-KB or unified conversation. */
export function removeKnowledgeBaseConversations(store, kbId) {
  store.remove(scopeKey(kbId))
  const global = store.restore('all')
  if (global?.messages?.some(m => m.citations?.some(c => c.knowledge_base_id === kbId))) store.remove('all')
}
