<script setup>
import {ref, computed, onMounted, onUnmounted, watch} from 'vue'

const TOKEN_KEY = 'knowops.token'

const kbs = ref([]), selected = ref('all'), docs = ref([]), tab = ref('chat')
const name = ref(''), description = ref(''), creating = ref(false), showCreate = ref(false)
const uploading = ref(false), asking = ref(false), expandContext = ref(false)
const question = ref(''), messages = ref([]), error = ref(''), notice = ref('')
const page = ref(0), loading = ref(false), action = ref(null)

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const me = ref(null), needsLogin = ref(false), loginToken = ref(''), loginError = ref(''), busyLogin = ref(false)

const showAdmin = ref(false), users = ref([]), adminForm = ref({email: '', display_name: '', role: 'viewer'})
const issuedToken = ref(''), adminBusy = ref(false)
const showMembers = ref(false), members = ref([]), memberForm = ref({email: '', role: 'viewer'})

const unified = computed(() => selected.value === 'all')
const kb = computed(() => kbs.value.find(k => k.id === selected.value))
const indexed = computed(() => docs.value.filter(d => d.index_status === 'indexed').length)
const isAdmin = computed(() => !!me.value?.is_admin)
const canAuthor = computed(() => !!me.value?.can_author)
const kbRole = computed(() => kb.value?.my_role || null)
const canWriteKb = computed(() => isAdmin.value || ['owner', 'editor'].includes(kbRole.value))
const canUpload = computed(() => canAuthor.value && canWriteKb.value)
const roleLabel = computed(() => ({admin: '管理员', editor: '知识管理员', viewer: '只读成员'}[me.value?.role] || me.value?.role || ''))
let timer, generation = 0

async function api(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 180000)
  const headers = {...(options.headers || {})}
  if (token.value) headers.Authorization = 'Bearer ' + token.value
  try {
    const r = await fetch('/api/v1' + path, {...options, headers, signal: controller.signal})
    const data = r.status === 204 ? null : await r.json()
    if (r.status === 401) {
      needsLogin.value = true
      throw new Error('登录已失效，请重新登录')
    }
    if (!r.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : '请求未通过校验，请检查输入')
    return data
  } finally {
    clearTimeout(timeout)
  }
}
function json(data) { return {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)} }
function patch(data) { return {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)} }
function fail(e) { error.value = e.name === 'AbortError' ? '请求超时，请稍后重试' : e.message }

async function loadKB() {
  const list = []
  let offset = 0
  while (true) {
    const part = await api('/knowledge-bases?limit=100&offset=' + offset)
    list.push(...part)
    if (part.length < 100) break
    offset += 100
  }
  kbs.value = list
  if (typeof selected.value === 'number' && !list.some(k => k.id === selected.value)) selected.value = list.length ? list[0].id : 'all'
}
async function loadDocs() {
  if (typeof selected.value !== 'number') return
  const id = selected.value, p = page.value, g = generation
  const data = await api(`/knowledge-bases/${id}/documents?limit=20&offset=${p * 20}`)
  if (g === generation && id === selected.value && p === page.value) docs.value = data
}
watch(selected, () => {
  if (unified.value) tab.value = 'chat'
  generation++; page.value = 0; docs.value = []; messages.value = []; error.value = ''; notice.value = ''
  if (showMembers.value) { members.value = []; showMembers.value = false }
  loadDocs().catch(fail)
})
async function create() {
  if (!name.value.trim()) return
  creating.value = true; error.value = ''
  try {
    const data = await api('/knowledge-bases', json({name: name.value.trim(), description: description.value}))
    await loadKB(); selected.value = data.id; showCreate.value = false; name.value = ''; description.value = ''
  } catch (e) { fail(e) } finally { creating.value = false }
}
async function upload(event) {
  const file = event.target.files[0]
  if (!file) return
  error.value = ''
  if (file.size > 10 * 1024 * 1024) { error.value = '文件不能超过 10 MiB'; event.target.value = ''; return }
  uploading.value = true
  const id = selected.value
  try {
    const form = new FormData(); form.append('file', file)
    const result = await api(`/knowledge-bases/${id}/documents`, {method: 'POST', body: form})
    if (id === selected.value) {
      notice.value = result.queued ? '文件已上传，解析与索引进度见下方。' : '文件已保存，但任务未入队，请点击重试解析。'
      page.value = 0; await loadDocs()
    }
  } catch (e) { fail(e) } finally { uploading.value = false; event.target.value = '' }
}
async function retry(d) {
  action.value = d.id; error.value = ''
  try {
    const path = d.status === 'parsed' ? 'index' : 'retry'
    const result = await api(`/document-versions/${d.version_id}/${path}`, {method: 'POST'})
    notice.value = result.queued ? '任务已投递，状态将自动刷新。' : '暂未入队，请稍后重试'
    await loadDocs()
  } catch (e) { fail(e) } finally { action.value = null }
}
async function ask() {
  if (!question.value.trim() || asking.value || !selected.value) return
  const text = question.value.trim(), id = selected.value, g = generation
  question.value = ''; messages.value.push({role: 'user', text}); asking.value = true; error.value = ''
  try {
    const result = await api('/chat/ask', json({question: text, ...(id === 'all' ? {scope: 'all'} : {knowledge_base_id: id}), top_k: 3, expand_context: expandContext.value}))
    if (g === generation) messages.value.push({role: 'assistant', text: result.answer, citations: result.citations, claims: result.claims, answerable: result.answerable})
  } catch (e) {
    if (g === generation) { question.value = text; fail(e) }
  } finally { asking.value = false }
}
async function changePage(delta) { page.value += delta; await loadDocs().catch(fail) }

async function signIn() {
  busyLogin.value = true; loginError.value = ''
  try {
    const r = await fetch('/api/v1/auth/me', {headers: loginToken.value.trim() ? {Authorization: 'Bearer ' + loginToken.value.trim()} : {}})
    if (!r.ok) throw new Error(r.status === 401 ? 'Token 无效、已吊销或用户已停用' : '登录失败，请稍后重试')
    const profile = await r.json()
    token.value = loginToken.value.trim()
    if (token.value) localStorage.setItem(TOKEN_KEY, token.value)
    else localStorage.removeItem(TOKEN_KEY)
    me.value = profile; needsLogin.value = false; loginToken.value = ''; loginError.value = ''
    await loadKB(); await loadDocs()
  } catch (e) { loginError.value = e.message } finally { busyLogin.value = false }
}
function signOut() {
  token.value = ''; localStorage.removeItem(TOKEN_KEY); me.value = null
  kbs.value = []; docs.value = []; messages.value = []; users.value = []; members.value = []
  showAdmin.value = false; showMembers.value = false; selected.value = 'all'; needsLogin.value = true
}
async function bootstrap() {
  loading.value = true
  try {
    me.value = await api('/auth/me')
    needsLogin.value = false
    await loadKB(); await loadDocs()
  } catch (e) {
    if (!needsLogin.value) fail(e)
  } finally { loading.value = false }
}

async function openAdmin() {
  showAdmin.value = true; issuedToken.value = ''; adminBusy.value = true
  try { users.value = await api('/admin/users') } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function createUser() {
  if (!adminForm.value.email.trim()) return
  adminBusy.value = true; error.value = ''
  try {
    const data = await api('/admin/users', json({...adminForm.value, email: adminForm.value.email.trim()}))
    adminForm.value = {email: '', display_name: '', role: 'viewer'}
    await openAdmin()
    notice.value = `已创建用户 ${data.email}；需要登录凭证时请点击该行的“签发 Token”。`
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function issueTokenFor(u) {
  adminBusy.value = true; error.value = ''
  try {
    const data = await api(`/admin/users/${u.id}/tokens`, {method: 'POST'})
    issuedToken.value = data.token; await openAdmin()
    notice.value = `已为 ${u.email} 签发 Token，仅显示一次，请立即复制。`
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function setUserRole(u, role) {
  adminBusy.value = true; error.value = ''
  try { await api(`/admin/users/${u.id}`, patch({role})); await openAdmin() } catch (e) { fail(e); await openAdmin() } finally { adminBusy.value = false }
}
async function toggleUserActive(u) {
  adminBusy.value = true; error.value = ''
  try { await api(`/admin/users/${u.id}`, patch({is_active: !u.is_active})); await openAdmin() } catch (e) { fail(e); await openAdmin() } finally { adminBusy.value = false }
}
async function revokeUserTokens(u) {
  adminBusy.value = true; error.value = ''
  try {
    const data = await api(`/admin/users/${u.id}/tokens`, {method: 'DELETE'})
    await openAdmin(); notice.value = `已吊销 ${u.email} 的 ${data.revoked} 个 Token。`
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}

async function openMembers() {
  if (typeof selected.value !== 'number') return
  showMembers.value = true; adminBusy.value = true
  try { members.value = await api(`/knowledge-bases/${selected.value}/members`) } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function addMember() {
  if (!memberForm.value.email.trim()) return
  adminBusy.value = true; error.value = ''
  try {
    await api(`/knowledge-bases/${selected.value}/members`, json({...memberForm.value, email: memberForm.value.email.trim()}))
    memberForm.value = {email: '', role: 'viewer'}
    await openMembers(); await loadKB()
    notice.value = '已更新知识库成员权限。'
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function removeMember(m) {
  adminBusy.value = true; error.value = ''
  try { await api(`/knowledge-bases/${selected.value}/members/${m.user_id}`, {method: 'DELETE'}); await openMembers(); await loadKB() } catch (e) { fail(e) } finally { adminBusy.value = false }
}

onMounted(async () => {
  await bootstrap()
  timer = setInterval(() => {
    if (!document.hidden && !needsLogin.value) loadDocs().catch(fail)
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>
<template>
<div class="shell">
<aside>
  <a class="brand" href="/ui/"><span class="logo">K</span> KnowOps<span class="dot">.</span></a>
  <div class="subtitle">企业知识 · 有据可循</div>
  <button class="kb" :class="{active:unified}" @click="selected='all';tab='chat'"><span>✳</span><span>统一问答</span><span class="arrow">›</span></button>
  <div class="side-heading">我的知识库 <button v-if="canAuthor" class="icon" aria-label="创建知识库" @click="showCreate=true">＋</button></div>
  <div v-if="loading" class="side-note">正在连接知识库…</div>
  <button v-for="item in kbs" :key="item.id" class="kb" :class="{active:selected===item.id}" @click="selected=item.id">
    <span>▤</span><span>{{item.name}}</span><span class="arrow">›</span>
  </button>
  <button v-if="canAuthor" class="new-kb" @click="showCreate=true">＋ 创建知识库</button>
  <div class="side-bottom">
    <span class="local-dot"></span>{{ me ? (me.local ? '本机开发空间' : me.email) : '正在确认身份…' }}<br>
    <small v-if="me">{{ roleLabel }}{{ me.local ? ' · 未启用鉴权模式' : '' }}</small>
    <button v-if="me && !me.local" class="text-button" @click="signOut">退出登录</button>
  </div>
</aside>
<main>
  <header>
    <div>
      <span class="eyebrow">WORKSPACE / KNOWLEDGE</span>
      <h1>{{unified?'统一问答':(kb?.name || '欢迎使用 KnowOps')}}</h1>
      <p>{{unified?'从全部知识库查找资料，无需先判断问题属于哪个库。':(kb?.description || '让散落的文档，成为随时可用的知识。')}}</p>
    </div>
    <div class="header-actions">
      <button v-if="isAdmin" class="api-link" @click="openAdmin">用户管理</button>
      <a class="api-link" href="/docs" target="_blank" rel="noopener">接口文档 ↗</a>
    </div>
  </header>
  <label class="scope-picker">检索范围<select v-model="selected" aria-label="检索范围"><option value="all">全部知识库 · 统一问答</option><option v-for="item in kbs" :key="item.id" :value="item.id">{{item.name}}</option></select></label>
  <label v-if="tab==='chat'" class="context-option"><input v-model="expandContext" type="checkbox" :disabled="asking">补充同文档资料<small>有助于查找前后条款，回答可能稍慢</small></label>
  <div class="toolbar">
    <nav>
      <button :class="{chosen:tab==='chat'}" @click="tab='chat'">知识问答</button>
      <button v-if="!unified" :class="{chosen:tab==='docs'}" @click="tab='docs'">文档管理 <span>{{docs.length}}</span></button>
    </nav>
    <span v-if="unified" class="caption">检索范围：全部 {{kbs.length}} 个知识库</span>
    <span v-else class="caption">当前页 {{indexed}} 份文档可检索{{ kbRole ? ' · 我的权限：'+({admin:'管理员',owner:'所有者',editor:'可编辑',viewer:'只读'}[kbRole]||kbRole) : '' }}</span>
  </div>
  <div v-if="error" role="alert" class="alert error">{{error}} <button @click="error=''" aria-label="关闭错误">×</button></div>
  <div v-if="notice" role="status" class="alert">{{notice}} <button @click="notice=''" aria-label="关闭提示">×</button></div>
  <section v-if="!kbs.length" class="welcome">
    <div class="hero-icon">▤</div>
    <h2>{{ canAuthor ? '从第一份知识开始' : '还没有你可以访问的知识库' }}</h2>
    <p>{{ canAuthor ? '创建知识库，上传制度、产品手册或 IT 操作文档。' : '请联系管理员把你加入相应的知识库。' }}</p>
    <button v-if="canAuthor" class="primary" @click="showCreate=true">创建知识库</button>
  </section>
  <section v-else-if="tab==='chat'" class="chat">
    <div class="conversation" aria-live="polite">
      <div v-if="!messages.length" class="welcome">
        <div class="hero-icon">✳</div>
        <span class="eyebrow">YOUR KNOWLEDGE, CONNECTED</span>
        <h2>答案，就在你的文档里。</h2>
        <p>{{unified?'直接提问，系统从你有权访问的知识库检索，引用会标明所属知识库。':'向「'+kb.name+'」提问，答案会附上可核对的原文来源。'}}</p>
        <div class="suggestions">
          <button @click="question='在家办公如何连接公司内网？'">在家如何连接公司内网？ ↗</button>
          <button v-if="canAuthor" @click="unified?showCreate=true:tab='docs'">{{unified?'创建知识库 ↗':'先上传一份文档 ↗'}}</button>
        </div>
        <small>每次提问独立检索，暂不使用对话历史。</small>
      </div>
      <article v-for="(m,i) in messages" :key="i" class="message" :class="m.role">
        <div class="avatar">{{m.role==='user'?'你':'K'}}</div>
        <div class="message-body">
          <b>{{m.role==='user'?'我的问题':'KnowOps'}}</b>
          <p>{{m.text}}</p>
          <span v-if="m.answerable===false" class="badge">资料不足</span>
          <div v-if="m.citations?.length" class="sources">
            <div class="eyebrow">参考来源 · {{m.citations.length}}</div>
            <details v-for="c in m.citations" :key="c.source_id">
              <summary><span class="source-no">{{c.source_id}}</span>{{c.filename}}<small v-if="c.knowledge_base_name">{{c.knowledge_base_name}}</small><small>{{c.page?'第 '+c.page+' 页':'切片 '+(c.position+1)}}</small></summary>
              <template v-for="(claim,j) in m.claims" :key="j"><blockquote v-for="(e,k) in claim.evidence.filter(e=>e.source_id===c.source_id)" :key="k">{{e.quote}}</blockquote></template>
              <p>{{c.content}}</p>
            </details>
          </div>
        </div>
      </article>
      <div v-if="asking" class="thinking">✳ 正在检索文档并组织答案，首次加载可能较慢…</div>
    </div>
    <form class="composer" @submit.prevent="ask">
      <textarea v-model="question" aria-label="输入问题" placeholder="输入你的问题，答案将附上原文来源…" maxlength="2000" :disabled="asking" @keydown.ctrl.enter.prevent="ask" @keydown.meta.enter.prevent="ask"></textarea>
      <div><small>答案由 AI 生成，请结合来源核对 · ⌘ / Ctrl + Enter 发送</small><button class="primary" :disabled="asking||!question.trim()" type="submit">{{asking?'回答中…':'发送问题 ↑'}}</button></div>
    </form>
  </section>
  <section v-else class="documents">
    <div class="document-heading">
      <div><h2>知识来源</h2><p>上传后自动解析与索引；状态每 5 秒刷新。</p></div>
      <div class="document-actions">
        <button v-if="canWriteKb" class="api-link" @click="openMembers">成员权限</button>
        <label v-if="canUpload" class="primary upload" :class="{disabled:uploading}">{{uploading?'正在上传…':'＋ 上传文档'}}<input type="file" accept=".txt,.md,.pdf" :disabled="uploading" @change="upload"></label>
      </div>
    </div>
    <div class="file-hint">支持 UTF-8 TXT、Markdown 和文本 PDF · 每份不超过 10 MiB · 不支持扫描件 OCR<span v-if="!canUpload"> · 你对该知识库只有查看权限</span></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>文档名称</th><th>解析</th><th>索引</th><th>切片</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="d in docs" :key="d.id">
            <td><span class="file-icon">▤</span>{{d.filename}}<small v-if="d.error||d.index_error" class="row-error">{{d.error||d.index_error}}</small></td>
            <td><span class="badge" :class="d.status">{{{pending:'待处理',parsed:'已解析',failed:'解析失败'}[d.status]||d.status}}</span></td>
            <td><span class="badge" :class="d.index_status">{{d.status!=='parsed'?'等待解析':({pending:'等待索引',indexed:'可检索',failed:'索引失败'}[d.index_status]||d.index_status)}}</span></td>
            <td>{{d.chunk_count}}</td>
            <td>
              <button v-if="canWriteKb && (d.status!=='parsed'||d.index_status!=='indexed')" class="text-button" :disabled="action===d.id" @click="retry(d)">{{action===d.id?'投递中…':d.status==='parsed'?'重试索引':'重试解析'}}</button>
              <span v-else-if="d.status==='parsed'&&d.index_status==='indexed'" class="ready">✓ 就绪</span>
              <span v-else class="ready">等待处理</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!docs.length" class="empty">{{loading?'正在加载…':'这里还没有文档，上传第一份资料开始使用。'}}</div>
    </div>
    <div class="pagination"><button :disabled="page===0" @click="changePage(-1)">上一页</button><span>第 {{page+1}} 页 · 每页 20 份</span><button :disabled="docs.length<20" @click="changePage(1)">下一页</button></div>
  </section>
  <footer>KnowOps <span>企业内部知识库问答平台</span><span>文档 → 检索 → 有据回答</span></footer>
</main>

<div v-if="showCreate" class="overlay" @click.self="showCreate=false">
  <form role="dialog" aria-modal="true" aria-label="创建知识库" class="modal" @submit.prevent="create">
    <div class="modal-heading"><h2>创建知识库</h2><button type="button" class="icon" @click="showCreate=false" aria-label="关闭">×</button></div>
    <p>按团队或主题整理资料。统一问答会检索你有权访问的全部知识库，也可选择单个知识库提问。</p>
    <label>知识库名称<input v-model="name" required maxlength="128" placeholder="例如：IT 运维知识库"></label>
    <label>描述（可选）<textarea v-model="description" maxlength="512" placeholder="这里保存哪些资料？"></textarea></label>
    <button class="primary" :disabled="creating||!name.trim()">{{creating?'创建中…':'创建知识库'}}</button>
  </form>
</div>

<div v-if="showMembers" class="overlay" @click.self="showMembers=false">
  <section role="dialog" aria-modal="true" aria-label="知识库成员权限" class="modal wide">
    <div class="modal-heading"><h2>成员权限 · {{kb?.name}}</h2><button type="button" class="icon" @click="showMembers=false" aria-label="关闭">×</button></div>
    <p>owner 与 editor 可以上传和维护文档，viewer 只能查看与提问。</p>
    <form class="inline-form" @submit.prevent="addMember">
      <input v-model="memberForm.email" type="email" required placeholder="成员邮箱（需已存在用户）" aria-label="成员邮箱">
      <select v-model="memberForm.role" aria-label="成员角色"><option value="viewer">viewer · 只读</option><option value="editor">editor · 可编辑</option><option value="owner">owner · 所有者</option></select>
      <button class="primary" :disabled="adminBusy||!memberForm.email.trim()">添加</button>
    </form>
    <div class="table-wrap">
      <table>
        <thead><tr><th>成员</th><th>角色</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="m in members" :key="m.user_id"><td>{{m.display_name}}<small>{{m.email}}</small></td><td><span class="badge">{{m.role}}</span></td><td><button class="text-button" :disabled="adminBusy" @click="removeMember(m)">移除</button></td></tr>
        </tbody>
      </table>
      <div v-if="!members.length" class="empty">还没有成员记录。</div>
    </div>
  </section>
</div>

<div v-if="showAdmin" class="overlay" @click.self="showAdmin=false">
  <section role="dialog" aria-modal="true" aria-label="用户管理" class="modal wide">
    <div class="modal-heading"><h2>用户管理</h2><button type="button" class="icon" @click="showAdmin=false" aria-label="关闭">×</button></div>
    <p>管理员可创建用户、签发与吊销 Token、调整角色；Token 只在签发时显示一次。</p>
    <form class="inline-form" @submit.prevent="createUser">
      <input v-model="adminForm.email" type="email" required placeholder="邮箱" aria-label="用户邮箱">
      <input v-model="adminForm.display_name" placeholder="显示名（可选）" aria-label="显示名">
      <select v-model="adminForm.role" aria-label="全局角色"><option value="viewer">viewer</option><option value="editor">editor</option><option value="admin">admin</option></select>
      <button class="primary" :disabled="adminBusy||!adminForm.email.trim()">创建用户</button>
    </form>
    <div v-if="issuedToken" class="token-callout">
      <b>新 Token（仅显示一次）</b>
      <code>{{issuedToken}}</code>
      <small>请立即复制保存。数据库只保存摘要，关闭后无法再次查看。</small>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>用户</th><th>角色</th><th>状态</th><th>有效 Token</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{u.display_name}}<small>{{u.email}}</small></td>
            <td>
              <select :value="u.role" :disabled="adminBusy" @change="setUserRole(u,$event.target.value)" aria-label="调整角色">
                <option value="viewer">viewer</option><option value="editor">editor</option><option value="admin">admin</option>
              </select>
            </td>
            <td><span class="badge" :class="{ready:u.is_active}">{{u.is_active?'启用':'停用'}}</span></td>
            <td>{{u.active_tokens}}</td>
            <td class="row-actions">
              <button class="text-button" :disabled="adminBusy" @click="issueTokenFor(u)">签发 Token</button>
              <button class="text-button" :disabled="adminBusy||!u.active_tokens" @click="revokeUserTokens(u)">吊销</button>
              <button class="text-button" :disabled="adminBusy" @click="toggleUserActive(u)">{{u.is_active?'停用':'启用'}}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!users.length" class="empty">正在加载用户…</div>
    </div>
  </section>
</div>

<div v-if="needsLogin" class="overlay">
  <form role="dialog" aria-modal="true" aria-label="登录" class="modal" @submit.prevent="signIn">
    <div class="modal-heading"><h2>登录 KnowOps</h2></div>
    <p>粘贴管理员签发的 API Token。Token 可在「用户管理」中签发，或在服务器上用 <code>scripts/manage_users.py</code> 生成。</p>
    <label>API Token<input v-model="loginToken" type="password" autocomplete="off" placeholder="knp_…" aria-label="API Token"></label>
    <div v-if="loginError" class="alert error">{{loginError}}</div>
    <button class="primary" :disabled="busyLogin">{{busyLogin?'验证中…':'登录'}}</button>
  </form>
</div>
</div></template>
