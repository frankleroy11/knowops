# 修复：切换知识库后问答记录消失

## 1. 现象与根因

用户报告：在统一问答里问出答案后，点击侧边栏另一个知识库、再切回统一问答，**刚才的问答没了**。

根因在 `frontend/src/App.vue` 里监听检索范围的地方——它**无条件清空对话**：

```js
watch(selected, () => {
  if (unified.value) tab.value = 'chat'
  generation++; page.value = 0; docs.value = []
  messages.value = []        // ← 每次切换范围都清空，切回来就什么也没有
  ...
})
```

`docs.value = []` 是对的（文档列表属于单个知识库），但 `messages` 不应该一起清。

## 2. 修复方式：每个检索范围各自保留记录

- 新增 `frontend/src/conversations.js`：
  - `scopeKey(selected)`：统一问答 → `'all'`，知识库 → 其 id；
  - `createConversationStore()`：按范围分桶（stash/restore/clear）；
  - `switchScope(store, {from, to, messages, question})`：**切换这一个动作本身**——先保存离开范围的记录，再返回进入范围的记录（没有则空）。
- `App.vue` 的监听改为调用 `switchScope`，并把结果写回 `messages`/`question`；
- **未发送的问题草稿也随范围保留**（切回来不用重打）；
- 凭据失效（401）与退出登录时调用 `conversations.clear()`，避免下一个登录者看到上一位的问答；
- 欢迎区文案更新为"每次提问独立检索；切换知识库会分别保留各自的问答记录。"

## 3. 可测性：把逻辑抽出来，用 Node 内置测试跑

这段逻辑不依赖 Vue，因此可以真正被测到（而不是只靠肉眼看）：

```bash
cd frontend && node --test test/*.test.mjs     # 9 项，无需任何新依赖
```

覆盖：范围键区分、分桶存取、**用户报告的完整路径**（统一问答提问 → 切库 → 切回，回答仍在）、
迟到的回答落回它被提问的那个范围、草稿保留、清空、以及一条**契约测试**：
`watch(selected)` 必须走 `switchScope` 且不得再出现 `messages.value = []`（防止有人把清空写回去）。

CI 前端任务已加入该步骤（`.github/workflows/ci.yml`，Node 22 自带 test runner）。

## 4. 真实浏览器验证（Chrome CDP）

用 Chrome headless + DevTools Protocol 驱动真实页面走了一遍用户路径（不是只跑单测）：

| 步骤 | 结果 |
|---|---|
| 打开 `/ui/`，处于统一问答 | ✅ |
| 输入问题并发送，等到回答 | ✅（无错误提示） |
| 会话包含提问 + 回答两条消息 | ✅ |
| 点侧边栏另一个知识库 | ✅ 标题切换、该范围初始为空 |
| **点回统一问答** | ✅ **刚才的问答仍在，回答文本一字不差** |
| 再切回那个知识库 | ✅ 它自己仍为空（各范围互不干扰） |

**10/10 通过**。截图见 `.tmp/conversation-preserved.png`（忽略，不入库）：
画面里能看到提问、回答、"资料不足"标记以及 👍/👎 反馈按钮。

> 说明：截图里那次回答是拒答。原因是浏览器默认 `top_k=3` 且未勾选"补充同文档资料"，
> 属于已记录的 NEW-07 类上下文不足行为；命令行加 `expand_context=true` 后回答是正确的
> （"财务负责人与总经理，7 个工作日"）。不是本次改动引入的回归。

## 5. 顺带处理的环境问题（本次也影响到了验证）

验证过程中 Milvus **第三次**因 etcd 租约丢失退出（前两次分别在 10-14 早、10-14 晚），
直接表现为"页面问不出答案"——第一次浏览器验证就是这样失败的（后端返回
`检索不可用`、健康检查 milvus unavailable）。

已做两处小改动，针对根因而不是只重启：

1. `docker-compose.yml` 给 `mysql/redis/etcd/minio/milvus` 加 `restart: unless-stopped`：
   Milvus 因租约超时自行退出后，Docker 会自动把它拉回来（数据在卷里，不丢）。
2. etcd 命令加 `--heartbeat-interval=250 --election-timeout=2500`（默认 100/1000）：
   机器负载高时更不容易丢租约；单节点 etcd 没有副作用。

应用后核对：容器全部 Up、`alembic 0009`、知识库 12、文档 232、切片 759、Milvus **758 行**、
健康检查 `ok`，`expand_context=true` 的问答返回正确。

## 6. 未做

- 会话**不持久化**：刷新页面或重开浏览器仍会清空（当前只在内存中按范围保留）。
  如需跨刷新保留，可把 `conversations` 落到 `sessionStorage`，并处理过期与清理。
- 各范围的会话没有条数上限；长时间使用需要截断策略。
