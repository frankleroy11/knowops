/**
 * 问答记录按“检索范围”分别保留：统一问答（all）与每个知识库各一份。
 *
 * 之前切换知识库会把 messages 直接清空，用户切走再切回就丢了刚才的问答；
 * 现在改为进入某范围前把当前记录存入对应桶、切回时取回。
 *
 * 纯逻辑、不依赖 Vue，便于用 `node --test` 直接测试。
 */

export function scopeKey(selected) {
  return selected === 'all' ? 'all' : String(selected)
}

export function createConversationStore() {
  const buckets = new Map()
  return {
    /** 保存某个范围的问答记录（连同未发送完的问题草稿）。 */
    stash(key, conversation) {
      if (!key) return
      buckets.set(key, conversation)
    },
    /** 取回某个范围的记录；没有则返回 null。 */
    restore(key) {
      return buckets.get(key) ?? null
    },
    has(key) {
      return buckets.has(key)
    },
    size() {
      return buckets.size
    },
    /** 退出登录或凭据失效时清空，避免下一个登录者看到上一位的问答。 */
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
