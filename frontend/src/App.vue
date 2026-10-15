<script setup>
import {ref, computed, onMounted, onUnmounted, watch, nextTick} from 'vue'
import {
  createConversationPersistence,
  createConversationStore,
  scopeKey,
  switchScope,
  removeKnowledgeBaseConversations
} from './conversations.js'

const TOKEN_KEY = 'knowops.token'
const METHOD_KEY = 'knowops.login_method'

const kbs = ref([]), selected = ref('all'), docs = ref([]), tab = ref('chat')
const name = ref(''), description = ref(''), creating = ref(false), showCreate = ref(false)
const uploading = ref(false), asking = ref(false), expandContext = ref(false)
const question = ref(''), messages = ref([]), error = ref(''), notice = ref('')
const page = ref(0), loading = ref(false), action = ref(null)

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const me = ref(null), needsLogin = ref(false), loginToken = ref(''), loginError = ref(''), busyLogin = ref(false), ssoEnabled = ref(false)
const loginEmail = ref(''), loginPassword = ref(''), busyPassword = ref(false)
const registrationEnabled = ref(false), registerMode = ref(false), busyRegister = ref(false), registerNotice = ref('')
const registration = ref({email:'',display_name:'',password:'',confirm_password:''})
const showLoginPassword = ref(false)
const userQuery = ref(''), userRoleFilter = ref(''), userStateFilter = ref(''), userPage = ref(0)
const passwordUser = ref(null), adminPassword = ref(''), adminPasswordConfirm = ref('')
const loginMethod = ref(localStorage.getItem(METHOD_KEY) || '')

const users = ref([]), adminForm = ref({email: '', display_name: '', role: 'viewer', tenant_id: '', password:''})
const tenants = ref([]), tenantForm = ref({name: '', slug: ''})
const kbAction = ref(null), kbName = ref(''), kbConfirmation = ref('')
const issuedToken = ref(''), adminBusy = ref(false)
const showMembers = ref(false), members = ref([]), memberForm = ref({email: '', role: 'viewer'})
const showReviews = ref(false), reviews = ref([]), reviewNote = ref('')
const auditLogs = ref([]), auditTenant = ref('')
const failures = ref([]), failurePage = ref(0)
const versionDoc = ref(null), versions = ref([]), deleteDoc = ref(null), deleteDocName = ref('')
async function exportAudit() {
  adminBusy.value = true
  try {
    const query = auditTenant.value === '' ? '' : '?tenant_id='+auditTenant.value
    const response = await fetch('/api/v1/admin/audit-logs/export'+query, {headers:token.value?{Authorization:'Bearer '+token.value}:{}})
    if (!response.ok) throw new Error('导出失败，请确认登录与权限')
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a'); link.href = url; link.download = 'knowops-audit.csv'; link.click()
    setTimeout(()=>URL.revokeObjectURL(url),1000)
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function loadFailures() {
  adminBusy.value = true
  try { failures.value = await api(`/admin/document-failures?offset=${failurePage.value*50}`) } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function openFailure(d) {
  const item = kbs.value.find(k=>k.id===d.knowledge_base_id)
  if (item) await manageKb(item)
}
async function openVersions(d) {
  versionDoc.value = d; versions.value = []; adminBusy.value = true
  try { versions.value = await api(`/documents/${d.id}/versions`) } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function publishVersion(v) {
  adminBusy.value = true
  try { await api(`/document-versions/${v.version_id}/publish`, {method:'POST'}); await openVersions(versionDoc.value); await loadDocs(); notice.value = '有效版本已切换。' } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function confirmDeleteDoc() {
  adminBusy.value = true
  try {
    const result = await api(`/documents/${deleteDoc.value.id}`, {...json({confirm_filename:deleteDocName.value}),method:'DELETE'})
    removeKnowledgeBaseConversations(conversations, selected.value); messages.value = []; question.value = ''; generation++; persistConversations(true)
    deleteDoc.value = null; versionDoc.value = null; await loadDocs()
    notice.value = result.file_cleanup_pending ? '文档已删除，部分文件等待存储回收。' : '文档及其全部版本、切片与向量已删除。'
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
const systemStatus = ref(null), systemLoading = ref(false), systemError = ref('')
const systemLabels = {mysql:'MySQL',redis:'Redis',milvus:'Milvus',worker:'Worker',jobs:'文档任务'}
const jobLabels = {pending:'等待处理',parsed:'解析完成',failed:'失败',indexing:'正在索引',indexed:'索引完成'}
const statusLabels = {ok:'正常',unknown:'待确认',unavailable:'不可用'}
async function loadSystemStatus() {
  if (systemLoading.value) return
  systemLoading.value = true; systemError.value = ''; systemStatus.value = null
  try { systemStatus.value = await api('/admin/system/status') }
  catch (e) { systemError.value = e.message }
  finally { systemLoading.value = false }
}

// 登录页（含二次验证码与自助重置）
const loginCode = ref(''), needCode = ref(false)
const forgotView = ref('none'), forgotEmail = ref(''), forgotToken = ref(''), forgotPassword = ref('')
const forgotNotice = ref(''), busyForgot = ref(false)
// 安全设置
const showSecurity = ref(false), securityError = ref(''), securityNotice = ref('')
const pwForm = ref({current_password: '', new_password: ''})
const totpSecret = ref(''), totpUri = ref(''), totpCode = ref(''), busySecurity = ref(false)
// 顶部导航的浮层
const showKbList = ref(false), showUserMenu = ref(false)

// 界面模式：企业用户工作台（问答为主） / 管理控制台（仅管理员可见）
const MODE_KEY = 'knowops.mode'
const mode = ref(localStorage.getItem(MODE_KEY) === 'console' ? 'console' : 'workspace')
const consoleSection = ref('knowledge')

const unified = computed(() => selected.value === 'all')
const kb = computed(() => kbs.value.find(k => k.id === selected.value))
const indexed = computed(() => docs.value.filter(d => d.index_status === 'indexed').length)
const isAdmin = computed(() => !!me.value?.is_admin)
const canAuthor = computed(() => !!me.value?.can_author)
const kbRole = computed(() => kb.value?.my_role || null)
const canWriteKb = computed(() => isAdmin.value || ['owner', 'editor'].includes(kbRole.value))
const canUpload = computed(() => canAuthor.value && canWriteKb.value)
const roleLabel = computed(() => ({admin: '管理员', editor: '知识管理员', viewer: '只读成员'}[me.value?.role] || me.value?.role || ''))
const browserStorage = (() => { try { return window.sessionStorage } catch (e) { return null } })()
const persistence = createConversationPersistence(browserStorage)
const conversations = createConversationStore()
conversations.load(persistence.load())
let activeScope = scopeKey(selected.value)
let timer, generation = 0, persistTimer = 0, clearingTimer = 0
const clearing = ref(false)

/** 把当前范围的记录写进桶并落盘（300ms 防抖，避免每敲一个字都写存储）。 */
function persistConversations(immediate = false) {
  const run = () => {
    conversations.stash(activeScope, {messages: messages.value, question: question.value})
    persistence.save(conversations.entries())
  }
  if (immediate) { clearTimeout(persistTimer); run(); return }
  clearTimeout(persistTimer)
  persistTimer = setTimeout(run, 300)
}

/** 清空“当前检索范围”的会话，需要点两次确认。 */
function clearConversation() {
  if (!clearing.value) {
    clearing.value = true
    clearTimeout(clearingTimer)
    clearingTimer = setTimeout(() => { clearing.value = false }, 3000)
    return
  }
  clearTimeout(clearingTimer)
  clearing.value = false
  messages.value = []
  question.value = ''
  conversations.stash(activeScope, {messages: [], question: ''})
  persistence.save(conversations.entries())
  notice.value = '已清空当前会话记录。'
}

async function api(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 180000)
  const headers = {...(options.headers || {})}
  if (token.value) headers.Authorization = 'Bearer ' + token.value
  try {
    const r = await fetch('/api/v1' + path, {...options, headers, signal: controller.signal})
    const data = r.status === 204 ? null : await r.json()
    if (r.status === 401) {
      conversations.clear(); persistence.clear(); messages.value = []
      needsLogin.value = true; clearAccountSecrets()
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
// 退出或会话过期时清除一次性凭据和密码表单，避免下一个账号看到残留。
function clearAccountSecrets() {
  issuedToken.value=''; passwordUser.value=null; adminPassword.value=''; adminPasswordConfirm.value=''; adminForm.value.password=''
}
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
  generation++; page.value = 0; docs.value = []; error.value = ''; notice.value = ''
  if (showMembers.value) { members.value = []; showMembers.value = false }
  // 每个检索范围各自保留问答记录：切走时存起来，切回时取回。
  const next = scopeKey(selected.value)
  const conversation = switchScope(conversations, {
    from: activeScope, to: next, messages: messages.value, question: question.value
  })
  messages.value = conversation.messages
  question.value = conversation.question
  activeScope = next
  persistConversations(true)
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
function openKbAction(item, kind) {
  kbAction.value = {id: item.id, name: item.name, kind}
  kbName.value = item.name; kbConfirmation.value = ''; error.value = ''
}
async function submitKbAction() {
  const target = kbAction.value
  if (!target || adminBusy.value) return
  adminBusy.value = true; error.value = ''
  try {
    if (target.kind === 'rename') {
      await api(`/knowledge-bases/${target.id}`, {...json({name: kbName.value.trim()}), method: 'PATCH'})
      notice.value = '知识库名称已更新。'
    } else {
      const result = await api(`/knowledge-bases/${target.id}`, {...json({confirm_name: kbConfirmation.value}), method: 'DELETE'})
      const interrupted = asking.value && (unified.value || selected.value === target.id)
      if (interrupted) generation++
      const hasDeleted = c => c?.messages?.some(m => m.citations?.some(s => s.knowledge_base_id === target.id))
      if (selected.value === target.id || (unified.value && hasDeleted({messages:messages.value}))) {
        messages.value = []; question.value = ''
      }
      await loadKB(); await nextTick()
      removeKnowledgeBaseConversations(conversations, target.id)
      if (unified.value && hasDeleted({messages:messages.value})) { messages.value = []; question.value = '' }
      persistConversations(true)
      notice.value = (result.file_cleanup_pending ? '知识库已删除，部分上传文件仍待管理员回收。' : '知识库及关联数据已删除。') + (interrupted?'正在进行的问答已失效，请重新提问。':'')
    }
    await loadKB(); kbAction.value = null
  } catch (e) { fail(e) } finally { adminBusy.value = false }
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
    if (mode.value==='console' && consoleSection.value==='failures') await loadFailures(); else await loadDocs()
  } catch (e) { fail(e) } finally { action.value = null }
}
async function ask() {
  if (!question.value.trim() || asking.value || !selected.value) return
  const text = question.value.trim(), id = selected.value, g = generation
  question.value = ''; messages.value.push({role: 'user', text}); asking.value = true; error.value = ''
  try {
    const result = await api('/chat/ask', json({question: text, ...(id === 'all' ? {scope: 'all'} : {knowledge_base_id: id}), top_k: 3, expand_context: expandContext.value}))
    if (g === generation) messages.value.push({role: 'assistant', text: result.answer, citations: result.citations, claims: result.claims, answerable: result.answerable, grounding_status: result.grounding_status})
  } catch (e) {
    if (g === generation) { question.value = text; fail(e) }
  } finally { asking.value = false; persistConversations() }
}
/** 线上反馈：把用户评价连同 grounding_status 一起回传，补齐评测闭环的线上部分。 */
async function sendFeedback(m, index, rating) {
  const question = messages.value[index - 1]?.text || ''
  if (!question || m.feedback) return
  try {
    const payload = {
      rating,
      question,
      answer: m.text || '',
      grounding_status: m.grounding_status || '',
      citation_count: (m.citations || []).length
    }
    if (unified.value) payload.scope = 'all'
    else { payload.scope = 'knowledge_base'; payload.knowledge_base_id = selected.value }
    await api('/feedback', json(payload))
    m.feedback = rating
    persistConversations()
  } catch (e) { fail(e) }
}
async function changePage(delta) { page.value += delta; await loadDocs().catch(fail) }

async function signIn() {
  busyLogin.value = true; loginError.value = ''
  try {
    const r = await fetch('/api/v1/auth/me', {headers: loginToken.value.trim() ? {Authorization: 'Bearer ' + loginToken.value.trim()} : {}})
    if (!r.ok) throw new Error(r.status === 401 ? 'Token 无效、已吊销或用户已停用' : '登录失败，请稍后重试')
    const profile = await r.json()
    token.value = loginToken.value.trim()
    if (token.value) {
      localStorage.setItem(TOKEN_KEY, token.value)
      localStorage.setItem(METHOD_KEY, 'token'); loginMethod.value = 'token'
    } else {
      localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(METHOD_KEY); loginMethod.value = ''
    }
    me.value = profile; needsLogin.value = false; loginToken.value = ''; loginError.value = ''
    await loadKB(); await loadDocs()
  } catch (e) { loginError.value = e.message } finally { busyLogin.value = false }
}
// 前端先检查密码确认；真正的格式、密码策略和空间隔离仍由后端执行。
// 注册成功不自动获取管理会话，返回登录并预填邮箱。
async function registerAccount() {
  if (registration.value.password!==registration.value.confirm_password) { registerNotice.value='两次密码不一致'; return }
  busyRegister.value=true; registerNotice.value=''
  try {
    const r=await fetch('/api/v1/auth/register',json(registration.value)); const data=await r.json()
    if (!r.ok) throw new Error(typeof data.detail==='string'?data.detail:'请检查邮箱、显示名和密码格式')
    loginEmail.value=registration.value.email; registration.value={email:'',display_name:'',password:'',confirm_password:''}
    registerMode.value=false; loginError.value=''; registerNotice.value=data.detail
  } catch(e) { registerNotice.value=e.message } finally { busyRegister.value=false }
}
// 管理员重置成员密码会使该成员旧会话失效；成功后立即清空表单中的明文。
async function resetUserPassword() {
  if (adminPassword.value!==adminPasswordConfirm.value) return
  adminBusy.value=true
  try {
    await api(`/admin/users/${passwordUser.value.id}/password`,json({password:adminPassword.value}))
    passwordUser.value=null; adminPassword.value=''; adminPasswordConfirm.value=''; await loadUsers()
    notice.value='密码已设置，旧登录凭据已吊销，请通知成员重新登录。'
  } catch(e) { fail(e) } finally { adminBusy.value=false }
}
// 邮箱密码登录先拿 Token，再查询 /auth/me，以后端身份决定可见功能。
// 服务端要求 TOTP 时才展示二次验证码输入。
async function passwordLogin() {
  busyPassword.value = true; loginError.value = ''
  try {
    const response = await fetch('/api/v1/auth/password/login', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: loginEmail.value.trim(), password: loginPassword.value, code: loginCode.value.trim()})
    })
    const data = await response.json()
    if (!response.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : '登录失败'
      if (detail === '需要二次验证码') needCode.value = true
      throw new Error(detail)
    }
    token.value = data.token
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(METHOD_KEY, 'password'); loginMethod.value = 'password'
    loginEmail.value = ''; loginPassword.value = ''; loginCode.value = ''; needCode.value = false
    needsLogin.value = false
    me.value = await api('/auth/me')
    await loadKB(); await loadDocs()
  } catch (e) { loginError.value = e.message } finally { busyPassword.value = false }
}
async function signOut() {
  const wasSso = loginMethod.value === 'oidc'
  let oidcLogoutUrl = ''
  if (token.value) {
    try {
      const result = await api('/auth/logout', {method: 'POST'})
      oidcLogoutUrl = result?.oidc_logout_url || ''
    } catch (e) { /* 本地清理优先 */ }
  }
  token.value = ''; clearAccountSecrets(); showSecurity.value=false
  conversations.clear(); persistence.clear()
  localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(METHOD_KEY); loginMethod.value = ''
  me.value = null; kbs.value = []; docs.value = []; messages.value = []; users.value = []; members.value = []
  showMembers.value = false; selected.value = 'all'; needsLogin.value = true
  mode.value = 'workspace'; consoleSection.value = 'knowledge'
  if (oidcLogoutUrl) location.href = oidcLogoutUrl
  else if (wasSso && ssoEnabled.value) location.href = '/api/v1/auth/oidc/logout'
}
function openSecurity() {
  showUserMenu.value = false
  showSecurity.value = true
  securityError.value = ''; securityNotice.value = ''
  pwForm.value = {current_password: '', new_password: ''}
  totpSecret.value = ''; totpUri.value = ''; totpCode.value = ''
}

async function changePassword() {
  busySecurity.value = true; securityError.value = ''; securityNotice.value = ''
  try {
    await api('/auth/password', json(pwForm.value))
    pwForm.value = {current_password: '', new_password: ''}
    showSecurity.value=false; await signOut(); loginError.value=''; registerNotice.value='密码已更新，请重新登录。'
  } catch (e) { securityError.value = e.message } finally { busySecurity.value = false }
}

async function startTotp() {
  busySecurity.value = true; securityError.value = ''; securityNotice.value = ''
  try {
    const data = await api('/auth/2fa/setup', {method: 'POST'})
    totpSecret.value = data.secret; totpUri.value = data.otpauth_uri
  } catch (e) { securityError.value = e.message } finally { busySecurity.value = false }
}

async function enableTotp() {
  busySecurity.value = true; securityError.value = ''; securityNotice.value = ''
  try {
    await api('/auth/2fa/enable', json({code: totpCode.value.trim()}))
    me.value = await api('/auth/me')
    totpSecret.value = ''; totpUri.value = ''; totpCode.value = ''
    securityNotice.value = '二次验证已开启，下次登录需要输入动态验证码。'
  } catch (e) { securityError.value = e.message } finally { busySecurity.value = false }
}

async function disableTotp() {
  busySecurity.value = true; securityError.value = ''; securityNotice.value = ''
  try {
    await api('/auth/2fa/disable', json({code: totpCode.value.trim()}))
    me.value = await api('/auth/me')
    totpCode.value = ''
    securityNotice.value = '二次验证已关闭。'
  } catch (e) { securityError.value = e.message } finally { busySecurity.value = false }
}

async function requestReset() {
  busyForgot.value = true; forgotNotice.value = ''
  try {
    const data = await api('/auth/password/forgot', json({email: forgotEmail.value.trim()}))
    forgotNotice.value = data.detail || '如果该邮箱存在，重置指引已发出。'
    if (data.dev_reset_token) { forgotToken.value = data.dev_reset_token; forgotNotice.value = '本地调试模式：已自动填入重置令牌。' }
    forgotView.value = 'reset'
  } catch (e) { forgotNotice.value = e.message } finally { busyForgot.value = false }
}

async function confirmReset() {
  busyForgot.value = true; forgotNotice.value = ''
  try {
    await api('/auth/password/reset', json({token: forgotToken.value.trim(), new_password: forgotPassword.value}))
    forgotView.value = 'none'; forgotToken.value = ''; forgotPassword.value = ''
    loginError.value = ''; notice.value = '密码已重置，请用新密码登录。'
  } catch (e) { forgotNotice.value = e.message } finally { busyForgot.value = false }
}

function pickKb(value) {
  showKbList.value = false
  if (value === 'all') { selected.value = 'all'; tab.value = 'chat' } else { selected.value = value }
}

async function loadSsoStatus() {
  try {
    const response = await fetch('/api/v1/auth/oidc/status')
    if (response.ok) ssoEnabled.value = !!(await response.json()).enabled
  } catch (e) {
    ssoEnabled.value = false
  }
}
function ssoLogin() {
  location.href = '/api/v1/auth/oidc/start'
}
async function bootstrap() {
  loading.value = true
  const saved = conversations.restore(activeScope)
  if (saved) { messages.value = saved.messages; question.value = saved.question }
  await loadSsoStatus()
  try { registrationEnabled.value=!!(await (await fetch('/api/v1/auth/options')).json()).registration_enabled } catch(e) { registrationEnabled.value=false }
  try {
    me.value = await api('/auth/me')
    needsLogin.value = false
    await loadKB(); await loadDocs()
  } catch (e) {
    if (!needsLogin.value) fail(e)
  } finally { loading.value = false }
}

async function loadTenants() {
  if (!me.value?.is_platform_admin) { tenants.value = []; return }
  try { tenants.value = await api('/admin/tenants') } catch (e) { tenants.value = [] }
}
async function createTenant() {
  if (!tenantForm.value.name.trim() || !tenantForm.value.slug.trim()) return
  adminBusy.value = true; error.value = ''
  try {
    const created = await api('/admin/tenants', json({name: tenantForm.value.name.trim(), slug: tenantForm.value.slug.trim()}))
    tenantForm.value = {name: '', slug: ''}
    await loadTenants()
    notice.value = `已创建租户 ${created.name}（id=${created.id}）`
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function setUserTenant(u, value) {
  adminBusy.value = true; error.value = ''
  try {
    await api(`/admin/users/${u.id}`, patch({tenant_id: value === '' ? null : Number(value)}))
    await loadUsers()
  } catch (e) { fail(e); await loadUsers() } finally { adminBusy.value = false }
}
// 搜索/筛选/分页交给后端；不能靠前端过滤实现租户隔离。
async function loadUsers() {
  adminBusy.value = true
  try { const query=new URLSearchParams({q:userQuery.value,limit:'50',offset:String(userPage.value*50)}); if(userRoleFilter.value) query.set('role',userRoleFilter.value); if(userStateFilter.value) query.set('active',userStateFilter.value); users.value = await api('/admin/users?'+query); await loadTenants() } catch (e) { fail(e) } finally { adminBusy.value = false }
}

/** 进入管理控制台：管理员专用界面，交付知识库/用户/租户/审计。 */
async function enterConsole(section = 'knowledge') {
  if (!isAdmin.value) return
  mode.value = 'console'; consoleSection.value = section
  localStorage.setItem(MODE_KEY, 'console')
  issuedToken.value = ''
  if (section === 'users' || section === 'tenants') await loadUsers()
  if (section === 'audit') { await loadTenants(); await loadAudit() }
  if (section === 'failures') await loadFailures()
  if (section === 'system' && me.value?.is_platform_admin) await loadSystemStatus()
  if (section === 'knowledge') await loadKB()
}

function exitConsole() {
  mode.value = 'workspace'
  localStorage.setItem(MODE_KEY, 'workspace')
}

/** 从控制台进入某个知识库的问答。 */
async function openKb(item) {
  selected.value = item.id
  exitConsole()
  tab.value = 'chat'
  await loadDocs().catch(fail)
}

/** 控制台内切到某个知识库的资料页（上传/审核/成员）。 */
async function manageKb(item) {
  selected.value = item.id
  exitConsole()
  tab.value = 'docs'
  await loadDocs().catch(fail)
}
async function createUser() {
  if (!adminForm.value.email.trim()) return
  adminBusy.value = true; error.value = ''
  try {
    const payload = {...adminForm.value, email: adminForm.value.email.trim()}
    if (!payload.password) delete payload.password
    if (payload.tenant_id === '') delete payload.tenant_id
    else payload.tenant_id = Number(payload.tenant_id)
    const data = await api('/admin/users', json(payload))
    adminForm.value = {email: '', display_name: '', role: 'viewer', tenant_id: '', password:''}
    await loadUsers()
    notice.value = `已创建用户 ${data.email}；可在该行设置登录密码，或签发 API Token。`
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function issueTokenFor(u) {
  adminBusy.value = true; error.value = ''
  try {
    const data = await api(`/admin/users/${u.id}/tokens`, {method: 'POST'})
    issuedToken.value = data.token; await loadUsers()
    notice.value = `已为 ${u.email} 签发 Token，仅显示一次，请立即复制。`
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function setUserRole(u, role) {
  adminBusy.value = true; error.value = ''
  try { await api(`/admin/users/${u.id}`, patch({role})); await loadUsers() } catch (e) { fail(e); await loadUsers() } finally { adminBusy.value = false }
}
async function toggleUserActive(u) {
  adminBusy.value = true; error.value = ''
  try { await api(`/admin/users/${u.id}`, patch({is_active: !u.is_active})); await loadUsers() } catch (e) { fail(e); await loadUsers() } finally { adminBusy.value = false }
}
async function revokeUserTokens(u) {
  adminBusy.value = true; error.value = ''
  try {
    const data = await api(`/admin/users/${u.id}/tokens`, {method: 'DELETE'})
    await loadUsers(); notice.value = `已吊销 ${u.email} 的 ${data.revoked} 个 Token。`
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

function publishLabel(d) {
  if (d.retired_at) return '已下架'
  if (d.review_status === 'pending') return '待审核'
  if (d.review_status === 'rejected') return '已驳回'
  if (d.is_current && (d.status!=='parsed' || d.index_status!=='indexed')) return '待处理完成'
  return d.is_current ? '已发布' : '未发布'
}
async function uploadVersion(d, event) {
  const file = event.target.files[0]
  if (!file) return
  error.value = ''; uploading.value = true
  try {
    const form = new FormData(); form.append('file', file)
    const result = await api(`/documents/${d.id}/versions`, {method: 'POST', body: form})
    notice.value = result.review_status === 'pending' ? `新版本 v${result.version} 已提交，审核通过后才参与检索。` : `新版本 v${result.version} 已上传并生效。`
    await loadDocs()
  } catch (e) { fail(e) } finally { uploading.value = false; event.target.value = '' }
}
async function retireDoc(d) {
  adminBusy.value = true; error.value = ''
  try {
    await api(`/documents/${d.id}/retire`, {method: 'POST'})
    notice.value = '文档已下架，不再参与检索；历史切片与向量仍保留。'
    await loadDocs()
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function openReviews() {
  if (typeof selected.value !== 'number') return
  showReviews.value = true; adminBusy.value = true
  try { reviews.value = await api(`/knowledge-bases/${selected.value}/reviews`) } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function decideReview(v, decision) {
  adminBusy.value = true; error.value = ''
  try {
    await api(`/document-versions/${v.version_id}/review`, json({decision, note: reviewNote.value}))
    reviewNote.value = ''
    await openReviews(); await loadDocs()
    notice.value = decision === 'approve' ? '已通过审核并发布该版本。' : '已驳回该版本。'
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function toggleKbReview() {
  if (typeof selected.value !== 'number') return
  adminBusy.value = true; error.value = ''
  try {
    const updated = await api(`/knowledge-bases/${selected.value}`, patch({review_required: !kb.value?.review_required}))
    await loadKB()
    notice.value = updated.review_required ? '已开启：本库新上传需审核通过后才可检索。' : '已关闭：本库上传即生效。'
  } catch (e) { fail(e) } finally { adminBusy.value = false }
}
async function loadAudit() {
  adminBusy.value = true
  const query = auditTenant.value === '' ? '' : `&tenant_id=${auditTenant.value}`
  try { auditLogs.value = await api(`/admin/audit-logs?limit=50${query}`) } catch (e) { fail(e) } finally { adminBusy.value = false }
}

watch(messages, () => persistConversations(), {deep: true})
watch(question, () => persistConversations())

onMounted(async () => {
  await bootstrap()
  timer = setInterval(() => {
    if (!document.hidden && !needsLogin.value) loadDocs().catch(fail)
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>
<template>
<div class="app">
  <!-- ================= 登录页（整页） ================= -->
  <div v-if="needsLogin || !me" class="login-page">
    <section class="login-hero">
      <a class="brand light" href="/ui/"><span class="logo">K</span> KnowOps<span class="dot">.</span></a>
      <h1>企业知识，<br>有据可循。</h1>
      <p>把制度、手册与操作文档集中起来。提问时直接给出答案，并附上可以核对的原文出处。</p>
      <ul class="login-points">
        <li>逐句引用原文，点开即可核对</li>
        <li>按知识库与租户隔离，权限到人</li>
        <li>支持企业 SSO 与二次验证</li>
      </ul>
      <div class="login-footnote">KnowOps · 企业内部知识库问答平台</div>
    </section>

    <section class="login-panel">
      <form v-if="registerMode" class="login-card" @submit.prevent="registerAccount">
        <h2>注册 KnowOps</h2><p class="muted">开放演示注册：每个账号获得独立空间，可创建知识库和管理成员。邮箱不作验证，不会加入其他人的空间。</p>
        <label>显示名<input v-model="registration.display_name" required minlength="2" maxlength="60" autocomplete="nickname" aria-label="注册显示名"></label>
        <label>邮箱<input v-model="registration.email" type="email" required maxlength="255" autocomplete="username" aria-label="注册邮箱"></label>
        <label>密码<input v-model="registration.password" type="password" required minlength="8" maxlength="256" autocomplete="new-password" aria-label="注册密码"></label>
        <label>确认密码<input v-model="registration.confirm_password" type="password" required autocomplete="new-password" aria-label="注册确认密码"></label>
        <p class="muted">至少 8 位，包含字母、数字和符号，不使用邮箱名或常见弱密码。</p>
        <div v-if="registerNotice" class="alert" role="alert">{{registerNotice}}</div>
        <button class="primary block" :disabled="busyRegister">{{busyRegister?'注册中…':'创建账号'}}</button>
        <button type="button" class="text-button" :disabled="busyRegister" @click="registerMode=false;registerNotice=''">已有账号，返回登录</button>
      </form>
      <form v-else-if="forgotView==='none'" class="login-card" @submit.prevent="passwordLogin">
        <h2>登录 KnowOps</h2>
        <p class="muted">成员与管理员使用同一个入口，登录后按账号角色展示可用功能。</p>
        <button v-if="ssoEnabled" type="button" class="ghost sso-button" @click="ssoLogin">使用企业 SSO 登录 →</button>
        <label>邮箱<input v-model="loginEmail" type="email" autocomplete="username" placeholder="you@corp.com" aria-label="邮箱" required></label>
        <label>密码<input v-model="loginPassword" :type="showLoginPassword?'text':'password'" autocomplete="current-password" aria-label="密码" required></label>
        <button type="button" class="text-button" @click="showLoginPassword=!showLoginPassword">{{showLoginPassword?'隐藏密码':'显示密码'}}</button>
        <div v-if="registerNotice" class="alert" role="status">{{registerNotice}}</div>
        <label v-if="needCode">二次验证码<input v-model="loginCode" inputmode="numeric" autocomplete="one-time-code" placeholder="6 位动态验证码" aria-label="二次验证码" maxlength="16"></label>
        <div v-if="loginError" role="alert" class="alert error">{{loginError}}</div>
        <button class="primary block" :disabled="busyPassword||!loginEmail.trim()||!loginPassword">{{busyPassword?'验证中…':'登录'}}</button>
        <div class="login-links">
          <button type="button" class="text-button" @click="forgotView='request'; forgotNotice=''">忘记密码？</button>
          <button v-if="registrationEnabled" type="button" class="text-button" @click="registerMode=true;registerNotice=''">注册账号</button>
          <span class="muted" style="font-size:12px">{{needCode?'该账号已开启二次验证':(registrationEnabled?'注册即可体验独立演示空间':'首次使用请联系管理员开通账号')}}</span>
        </div>
        <details class="token-login"><summary>改用 API Token 登录</summary>
          <label>API Token<input v-model="loginToken" type="password" autocomplete="off" placeholder="knp_…" aria-label="API Token"></label>
          <button type="button" class="ghost" :disabled="busyLogin" @click="signIn">{{busyLogin?'验证中…':'用 Token 登录'}}</button>
        </details>
      </form>

      <form v-else-if="forgotView==='request'" class="login-card" @submit.prevent="requestReset">
        <h2>重置密码</h2>
        <p class="muted">填写账号邮箱。系统会生成一次性重置令牌，由管理员转交给你（本部署尚未接入邮件通道）。</p>
        <label>邮箱<input v-model="forgotEmail" type="email" required autocomplete="username" placeholder="you@corp.com" aria-label="邮箱"></label>
        <div v-if="forgotNotice" class="alert">{{forgotNotice}}</div>
        <button class="primary block" :disabled="busyForgot||!forgotEmail.trim()">{{busyForgot?'提交中…':'提交申请'}}</button>
        <div class="login-links"><button type="button" class="text-button" @click="forgotView='none'">← 返回登录</button></div>
      </form>

      <form v-else class="login-card" @submit.prevent="confirmReset">
        <h2>设置新密码</h2>
        <p class="muted">粘贴管理员转交的重置令牌，并设置新密码（至少 8 位，需含字母与数字）。</p>
        <label>重置令牌<input v-model="forgotToken" required placeholder="粘贴一次性令牌" aria-label="重置令牌"></label>
        <label>新密码<input v-model="forgotPassword" type="password" required autocomplete="new-password" aria-label="新密码"></label>
        <div v-if="forgotNotice" class="alert error">{{forgotNotice}}</div>
        <button class="primary block" :disabled="busyForgot||!forgotToken.trim()||!forgotPassword">{{busyForgot?'提交中…':'重置密码'}}</button>
        <div class="login-links"><button type="button" class="text-button" @click="forgotView='none'">← 返回登录</button></div>
      </form>
    </section>
  </div>

  <!-- ================= 主界面 ================= -->
  <template v-else>
    <header class="topbar">
      <a class="brand" href="/ui/"><span class="logo">K</span> KnowOps<span class="dot">.</span></a>

      <div v-if="mode==='workspace'" class="scope-switch">
        <button type="button" class="scope-button" :aria-expanded="showKbList" @click="showKbList=!showKbList">
          <span class="scope-icon">{{unified?'✳':'▤'}}</span>
          <span class="scope-text"><small>检索范围</small><b>{{unified?'全部知识库':(kb?.name||'选择知识库')}}</b></span>
          <span class="caret">▾</span>
        </button>
        <div v-if="showKbList" class="menu-panel">
          <button type="button" class="kb-item" :class="{active:unified}" @click="pickKb('all')">✳ 统一问答<small>全部 {{kbs.length}} 个知识库</small></button>
          <div class="menu-divider"></div>
          <div class="menu-label">我的知识库</div>
          <div v-if="loading" class="menu-note">正在连接知识库…</div>
          <button v-for="item in kbs" :key="item.id" type="button" class="kb-item" :class="{active:selected===item.id}" @click="pickKb(item.id)">
            ▤ {{item.name}}<small>{{item.my_role||''}}</small>
          </button>
          <div v-if="!kbs.length && !loading" class="menu-note">还没有可访问的知识库</div>
          <template v-if="canAuthor">
            <div class="menu-divider"></div>
            <button type="button" class="kb-item" @click="showCreate=true; showKbList=false">＋ 创建知识库</button>
          </template>
        </div>
      </div>

      <nav v-if="mode==='workspace'" class="topnav">
        <button :class="{chosen:tab==='chat'}" @click="tab='chat'">知识问答</button>
        <button v-if="!unified" :class="{chosen:tab==='docs'}" @click="tab='docs'">资料<span class="pill">{{docs.length}}</span></button>
      </nav>
      <nav v-else class="topnav">
        <button :class="{chosen:consoleSection==='knowledge'}" @click="enterConsole('knowledge')">知识库</button>
        <button :class="{chosen:consoleSection==='users'}" @click="enterConsole('users')">用户</button>
        <button v-if="me.is_platform_admin" :class="{chosen:consoleSection==='tenants'}" @click="enterConsole('tenants')">租户</button>
        <button v-if="me.is_platform_admin" :class="{chosen:consoleSection==='system'}" @click="enterConsole('system')">系统状态</button>
        <button :class="{chosen:consoleSection==='failures'}" @click="enterConsole('failures')">失败任务</button>
        <button :class="{chosen:consoleSection==='audit'}" @click="enterConsole('audit')">审计</button>
      </nav>

      <div class="topbar-right">
        <button v-if="isAdmin && mode==='workspace'" class="ghost strong" @click="enterConsole('knowledge')">管理控制台</button>
        <button v-if="isAdmin && mode==='console'" class="ghost" @click="exitConsole()">← 返回问答</button>
        <a class="ghost" href="/docs" target="_blank" rel="noopener">接口文档 ↗</a>
        <div class="user-menu">
          <button type="button" class="avatar-button" :aria-expanded="showUserMenu" @click="showUserMenu=!showUserMenu">
            <span class="avatar">{{(me.display_name||me.email||'?').slice(0,1).toUpperCase()}}</span>
            <span class="user-meta"><b>{{me.display_name||me.email}}</b><small>{{roleLabel}}<template v-if="me.is_platform_admin"> · 平台管理员</template></small></span>
          </button>
          <div v-if="showUserMenu" class="menu-panel">
            <div class="menu-label">{{me.email}}</div>
            <div class="menu-note">{{me.local?'本机开发空间（未启用鉴权）':(me.is_platform_admin?'平台管理员':(me.tenant_id?'租户 '+me.tenant_id:'普通成员'))}}{{me.totp_enabled?' · 已开启二次验证':''}}</div>
            <div class="menu-divider"></div>
            <button v-if="!me.local" type="button" class="kb-item" @click="openSecurity">安全设置<small>{{me.totp_enabled?'二次验证已开':'改密码 / 二次验证'}}</small></button>
            <button type="button" class="kb-item" @click="showUserMenu=false; signOut()">{{me.local?'重新加载':'退出登录'}}</button>
          </div>
        </div>
      </div>
    </header>

    <main v-if="mode==='workspace'" class="workspace">
      <div class="page-head">
        <div>
          <span class="eyebrow">WORKSPACE / KNOWLEDGE</span>
          <h1>{{unified?'统一问答':(kb?.name||'欢迎使用 KnowOps')}}</h1>
          <p>{{unified?'从全部知识库查找资料，无需先判断问题属于哪个库。':(kb?.description||'让散落的文档，成为随时可用的知识。')}}</p>
        </div>
      </div>

      <div class="toolbar">
        <button v-if="tab==='chat' && messages.length" type="button" class="text-button" @click="clearConversation">
          {{clearing?'再点一次确认清空':'清空当前会话'}}
        </button>
        <span v-if="unified" class="caption">检索范围：全部 {{kbs.length}} 个知识库</span>
        <span v-else class="caption">当前页 {{indexed}} 份文档可检索{{kbRole?' · 我的权限：'+({admin:'管理员',owner:'所有者',editor:'可编辑',viewer:'只读'}[kbRole]||kbRole):''}}</span>
      </div>

      <div v-if="error" role="alert" class="alert error">{{error}} <button @click="error=''" aria-label="关闭错误">×</button></div>
      <div v-if="notice" role="status" class="alert">{{notice}} <button @click="notice=''" aria-label="关闭提示">×</button></div>

      <section v-if="!kbs.length" class="welcome">
        <div class="hero-icon">▤</div>
        <h2>{{canAuthor?'从第一份知识开始':'还没有你可以访问的知识库'}}</h2>
        <p>{{canAuthor?'创建知识库，上传制度、产品手册或 IT 操作文档。':'请联系管理员把你加入相应的知识库。'}}</p>
        <button v-if="canAuthor" class="primary" @click="showCreate=true">创建知识库</button>
      </section>

      <section v-else-if="tab==='chat'" class="chat">
        <label class="context-option"><input v-model="expandContext" type="checkbox" :disabled="asking">补充同文档资料<small>有助于查找前后条款，回答可能稍慢</small></label>
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
            <small>每次提问独立检索；切换知识库会分别保留各自的问答记录。</small>
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
              <div v-if="m.role==='assistant'" class="feedback">
                <template v-if="!m.feedback">
                  <button type="button" @click="sendFeedback(m,i,'helpful')">👍 有帮助</button>
                  <button type="button" @click="sendFeedback(m,i,'not_helpful')">👎 没帮助</button>
                </template>
                <span v-else class="ready">已记录反馈，谢谢</span>
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
            <label v-if="canWriteKb" class="policy-toggle"><input type="checkbox" :checked="!!kb?.review_required" :disabled="adminBusy" @change="toggleKbReview">上传需审核</label>
            <button v-if="canWriteKb" class="ghost" @click="openReviews">待审版本</button>
            <button v-if="canWriteKb" class="ghost" @click="openMembers">成员权限</button>
            <label v-if="canUpload" class="primary upload" :class="{disabled:uploading}">{{uploading?'正在上传…':'＋ 上传文档'}}<input type="file" accept=".txt,.md,.pdf" :disabled="uploading" @change="upload"></label>
          </div>
        </div>
        <div class="file-hint">支持 UTF-8 TXT、Markdown 和文本 PDF · 每份不超过 10 MiB · 不支持扫描件 OCR<span v-if="!canUpload"> · 你对该知识库只有查看权限</span></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>文档名称</th><th>解析</th><th>索引</th><th>切片</th><th>发布</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="d in docs" :key="d.id">
                <td><span class="file-icon">▤</span>{{d.filename}}<small v-if="d.error||d.index_error" class="row-error">{{d.error||d.index_error}}</small></td>
                <td><span class="badge" :class="d.status">{{{pending:'待处理',parsed:'已解析',failed:'解析失败'}[d.status]||d.status}}</span></td>
                <td><span class="badge" :class="d.index_status">{{d.status!=='parsed'?'等待解析':({pending:'等待索引',indexed:'可检索',failed:'索引失败'}[d.index_status]||d.index_status)}}</span></td>
                <td>{{d.chunk_count}}</td>
                <td><span class="badge" :class="{ready:!d.retired_at&&d.review_status==='approved'&&d.is_current}">{{publishLabel(d)}}</span><small v-if="d.version">v{{d.version}}</small></td>
                <td class="row-actions">
                  <button v-if="canWriteKb && (d.status==='failed'||(d.status==='parsed'&&['pending','failed'].includes(d.index_status)))" class="text-button" :disabled="action===d.id" @click="retry(d)">{{action===d.id?'投递中…':d.status==='parsed'?'重试索引':'重试解析'}}</button>
                  <span v-else-if="d.status==='parsed'&&d.index_status==='indexed'" class="ready">✓ 就绪</span>
                  <span v-else class="ready">等待处理</span>
                  <button class="text-button" :disabled="adminBusy" @click="openVersions(d)">版本历史</button>
                  <button v-if="isAdmin" class="text-button" :disabled="adminBusy" @click="deleteDoc=d;deleteDocName=''">删除文档</button>
                  <label v-if="canWriteKb" class="text-button">上传新版本<input type="file" accept=".txt,.md,.pdf" hidden @change="uploadVersion(d,$event)"></label>
                  <button v-if="canWriteKb && !d.retired_at" class="text-button" :disabled="adminBusy" @click="retireDoc(d)">下架</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!docs.length" class="empty">{{loading?'正在加载…':'这里还没有文档，上传第一份资料开始使用。'}}</div>
        </div>
        <div class="pagination"><button :disabled="page===0" @click="changePage(-1)">上一页</button><span>第 {{page+1}} 页 · 每页 20 份</span><button :disabled="docs.length<20" @click="changePage(1)">下一页</button></div>
      </section>
    </main>

    <main v-else class="workspace wide">
      <div class="page-head">
        <div>
          <span class="eyebrow">ADMIN CONSOLE</span>
          <h1>{{({knowledge:'知识库管理',users:'用户管理',tenants:'租户管理',audit:'审计日志',system:'系统状态',failures:'失败任务'})[consoleSection]}}</h1>
          <p>{{({knowledge:'创建与维护知识库；进入某个知识库可上传资料、审核版本、分配成员。',users:'创建账号、调整角色与租户、签发或吊销 Token。',tenants:'平台级租户的新建与查看，所有数据按租户隔离。',audit:'谁在何时对哪个对象做了什么；可按租户筛选并导出 CSV。',system:'检查基础服务连接、Worker 响应和文档任务状态。',failures:'定位解析与索引失败，查看原因并按需重试。'})[consoleSection]}}</p>
        </div>
      </div>

      <section v-if="consoleSection==='knowledge'" class="console">
        <form class="console-card" @submit.prevent="create">
          <h3>新建知识库</h3>
          <p class="muted">按团队或主题整理资料。统一问答会检索你有权访问的全部知识库。</p>
          <div class="inline-form">
            <input v-model="name" required maxlength="128" placeholder="知识库名称，例如：IT 运维知识库" aria-label="知识库名称">
            <input v-model="description" maxlength="512" placeholder="描述（可选）" aria-label="知识库描述">
            <button class="primary" :disabled="creating||!name.trim()">{{creating?'创建中…':'创建知识库'}}</button>
          </div>
        </form>
        <div class="table-wrap">
          <table>
            <thead><tr><th>知识库</th><th>我的权限</th><th>上传需审核</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in kbs" :key="item.id">
                <td>{{item.name}}<small v-if="item.description">{{item.description}}</small></td>
                <td><span class="badge">{{item.my_role||'—'}}</span></td>
                <td><span class="badge" :class="{ready:item.review_required}">{{item.review_required?'已开启':'未开启'}}</span></td>
                <td class="row-actions">
                  <button class="text-button" :disabled="adminBusy" @click="openKbAction(item,'rename')">改名</button>
                  <button class="text-button" :disabled="adminBusy" @click="openKbAction(item,'delete')">删除</button>
                  <button class="text-button" @click="openKb(item)">进入问答</button>
                  <button class="text-button" @click="manageKb(item)">资料与上传</button>
                  <button class="text-button" @click="selected=item.id; openMembers()">成员权限</button>
                  <button class="text-button" @click="selected=item.id; openReviews()">待审版本</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!kbs.length" class="empty">还没有知识库，先在上方创建一个。</div>
        </div>
      </section>

      <section v-else-if="consoleSection==='users'" class="console">
        <form class="console-card" @submit.prevent="createUser">
          <h3>新建用户</h3>
          <p class="muted">为当前空间添加成员，可填写初始密码；留空时稍后通过“设置密码”或 API Token 开通登录。</p>
          <div class="inline-form">
            <input v-model="adminForm.email" type="email" required placeholder="邮箱" aria-label="用户邮箱">
            <input v-model="adminForm.display_name" placeholder="显示名（可选）" aria-label="显示名">
            <input v-model="adminForm.password" type="password" autocomplete="new-password" minlength="8" placeholder="初始密码（可选）" aria-label="成员初始密码">
            <select v-model="adminForm.role" aria-label="全局角色"><option value="viewer">viewer · 只读</option><option value="editor">editor · 可编辑</option><option value="admin">admin · 管理员</option></select>
            <select v-if="tenants.length" v-model="adminForm.tenant_id" aria-label="所属租户">
              <option value="">平台级（不属于租户）</option>
              <option v-for="t in tenants" :key="t.id" :value="t.id">{{t.name}}</option>
            </select>
            <button class="primary" :disabled="adminBusy||!adminForm.email.trim()">创建用户</button>
          </div>
        </form>
        <form class="console-toolbar" @submit.prevent="userPage=0;loadUsers()">
          <input v-model="userQuery" placeholder="搜索邮箱或显示名" aria-label="搜索用户">
          <select v-model="userRoleFilter" aria-label="筛选角色"><option value="">全部角色</option><option value="admin">管理员</option><option value="editor">编辑者</option><option value="viewer">只读成员</option></select>
          <select v-model="userStateFilter" aria-label="筛选状态"><option value="">全部状态</option><option value="true">启用</option><option value="false">停用</option></select>
          <button :disabled="adminBusy">搜索</button>
        </form>
        <div v-if="issuedToken" class="token-callout">
          <b>新 Token（仅显示一次）</b>
          <code>{{issuedToken}}</code>
          <small>请立即复制保存。数据库只保存摘要，关闭后无法再次查看。</small>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>用户</th><th>角色</th><th>租户</th><th>状态</th><th>登录方式 / 有效 Token</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td>{{u.display_name || u.email}}<small v-if="u.display_name && u.display_name !== u.email">{{u.email}}</small></td>
                <td>
                  <select :value="u.role" :disabled="adminBusy||u.id===me.id" aria-label="调整角色" @change="setUserRole(u,$event.target.value)">
                    <option value="viewer">viewer</option><option value="editor">editor</option><option value="admin">admin</option>
                  </select>
                </td>
                <td>
                  <select v-if="me?.is_platform_admin" :value="u.tenant_id ?? ''" :disabled="adminBusy||u.id===me.id" aria-label="调整租户" @change="setUserTenant(u,$event.target.value)">
                    <option value="">平台级</option>
                    <option v-for="t in tenants" :key="t.id" :value="t.id">{{t.name}}</option>
                  </select>
                  <span v-else class="badge">{{u.tenant_id ?? '—'}}</span>
                </td>
                <td><span class="badge" :class="{ready:u.is_active}">{{u.is_active?'启用':'停用'}}</span></td>
                <td>{{u.password_configured?'密码已设置':'未设置密码'}} · {{u.active_tokens}}<small v-if="u.locked_until">锁定至 {{u.locked_until}}</small></td>
                <td class="row-actions">
                  <button v-if="u.id!==me.id" class="text-button" :disabled="adminBusy" @click="passwordUser=u;adminPassword='';adminPasswordConfirm=''">设置密码</button>
                  <button class="text-button" :disabled="adminBusy||!u.is_active" @click="issueTokenFor(u)">签发 Token</button>
                  <button class="text-button" :disabled="adminBusy||!u.active_tokens" @click="revokeUserTokens(u)">吊销</button>
                  <button class="text-button" :disabled="adminBusy||u.id===me.id" @click="toggleUserActive(u)">{{u.is_active?'停用':'启用'}}</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!users.length" class="empty">{{adminBusy?'正在加载用户…':'没有符合条件的用户。'}}</div>
          <div class="pagination"><button :disabled="adminBusy||userPage===0" @click="userPage--;loadUsers()">上一页</button><span>第 {{userPage+1}} 页 · 每页 50 人</span><button :disabled="adminBusy||users.length<50" @click="userPage++;loadUsers()">下一页</button></div>
        </div>
      </section>

      <section v-else-if="consoleSection==='tenants'" class="console">
        <form class="console-card" @submit.prevent="createTenant">
          <h3>新建租户</h3>
          <p class="muted">租户之间的知识库、用户、审计完全隔离；租户管理员只能看到本租户数据。</p>
          <div class="inline-form">
            <input v-model="tenantForm.name" required placeholder="租户名称" aria-label="租户名称">
            <input v-model="tenantForm.slug" required placeholder="租户标识（英文小写）" aria-label="租户标识">
            <button class="primary" :disabled="adminBusy||!tenantForm.name.trim()||!tenantForm.slug.trim()">创建租户</button>
          </div>
        </form>
        <div class="table-wrap">
          <table>
            <thead><tr><th>租户</th><th>标识</th><th>用户数</th></tr></thead>
            <tbody>
              <tr v-for="t in tenants" :key="t.id">
                <td>{{t.name}}</td>
                <td><code>{{t.slug}}</code></td>
                <td>{{users.filter(u => u.tenant_id === t.id).length}}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!tenants.length" class="empty">当前只有默认租户。</div>
        </div>
      </section>

      <section v-else-if="consoleSection==='failures'" class="console">
        <div class="console-toolbar"><button :disabled="adminBusy" @click="loadFailures">刷新失败任务</button></div>
        <p class="muted">无效编码、扫描 PDF 等内容问题需要修正原文件后上传新版本；重复解析不会自动修复。重试仅投递该版本的失败阶段。</p>
        <div class="table-wrap"><table><thead><tr><th>知识库</th><th>文档 / 版本</th><th>失败阶段</th><th>原因</th><th>操作</th></tr></thead>
          <tbody><tr v-for="d in failures" :key="d.version_id"><td>{{d.knowledge_base_name}}</td><td>{{d.filename}} · v{{d.version}}</td><td>{{d.stage==='parse'?'解析':'索引'}}</td><td>{{d.error || '未记录原因'}}</td><td class="row-actions"><button :disabled="adminBusy" @click="openFailure(d)">查看资料</button><button :disabled="adminBusy||action===d.id" @click="retry(d)">重试{{d.stage==='parse'?'解析':'索引'}}</button></td></tr></tbody></table>
          <div v-if="!failures.length" class="empty">当前页没有失败记录。</div></div>
        <div class="pagination"><button :disabled="adminBusy||failurePage===0" @click="failurePage--;loadFailures()">上一页</button><span>第 {{failurePage+1}} 页</span><button :disabled="adminBusy||failures.length<50" @click="failurePage++;loadFailures()">下一页</button></div>
      </section>

      <section v-else-if="consoleSection==='system'" class="console" aria-label="系统状态">
        <div class="console-toolbar">
          <button class="primary" :disabled="systemLoading" @click="loadSystemStatus">{{systemLoading?'正在检查…':'刷新状态'}}</button>
          <span v-if="systemStatus" class="muted">检查时间：{{new Date(systemStatus.checked_at).toLocaleString()}}</span>
        </div>
        <p v-if="systemError" role="alert">检查请求失败：{{systemError}}。请刷新重试。</p>
        <p v-if="systemLoading" role="status">正在检查服务，请稍候。</p>
        <template v-if="systemStatus">
          <p role="status">{{systemStatus.status==='ok'?'各项检查正常':'部分状态异常或待确认，请查看下方详情。'}}</p>
          <div class="table-wrap"><table>
            <thead><tr><th>服务</th><th>状态</th><th>检查耗时</th><th>说明</th></tr></thead>
            <tbody><tr v-for="(item,key) in systemStatus.checks" :key="key">
              <td>{{systemLabels[key] || key}}</td><td><span class="badge" :class="{ready:item.status==='ok'}">{{key==='jobs' && item.status==='ok'?'统计成功':(statusLabels[item.status] || item.status)}}</span></td>
              <td>{{item.latency_ms}} ms</td><td>{{item.detail}}<template v-if="key==='worker'"> · 响应节点 {{item.workers ?? 0}}</template></td>
            </tr></tbody>
          </table></div>
          <div v-if="systemStatus.checks.jobs.status==='ok'" class="console-card">
            <h3>文档处理状态</h3>
            <p v-if="systemStatus.checks.jobs.parsing.failed || systemStatus.checks.jobs.indexing.failed" role="status">存在处理失败的记录，请到对应知识库的资料页查看错误并决定是否重试。</p>
            <p>解析：<span v-for="(count,state) in systemStatus.checks.jobs.parsing" :key="state">{{jobLabels[state] || state}} {{count}} · </span></p>
            <p>索引：<span v-for="(count,state) in systemStatus.checks.jobs.indexing" :key="state">{{jobLabels[state] || state}} {{count}} · </span></p>
          </div>
          <p class="muted">这是手动刷新时的状态快照。Worker 无响应可能是正在执行长任务；全部正常也不代表问答质量或完整上传链路已通过验证。</p>
        </template>
      </section>

      <section v-else class="console">
        <div class="console-toolbar">
          <select v-if="me?.is_platform_admin" v-model="auditTenant" aria-label="按租户筛选" @change="loadAudit">
            <option value="">全部租户</option>
            <option v-for="t in tenants" :key="t.id" :value="t.id">{{t.name}}</option>
          </select>
          <span class="muted">最近 50 条</span>
          <button class="ghost" :disabled="adminBusy" @click="exportAudit">导出 CSV ↘</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>时间</th><th>操作者</th><th>租户</th><th>动作</th><th>对象</th><th>详情</th></tr></thead>
            <tbody>
              <tr v-for="a in auditLogs" :key="a.id">
                <td>{{(a.created_at||'').replace('T',' ').slice(0,19)}}</td>
                <td>{{a.actor_email || '本地管理员'}}</td>
                <td>{{a.tenant_id ?? '平台级'}}</td>
                <td><span class="badge">{{a.action}}</span></td>
                <td>{{a.object_type}}{{a.object_id ? '#'+a.object_id : ''}}</td>
                <td>{{a.detail}}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!auditLogs.length" class="empty">还没有审计记录。</div>
        </div>
      </section>
    </main>

    <footer>KnowOps <span>企业内部知识库问答平台</span><span>文档 → 检索 → 有据回答</span></footer>
  </template>

  <div v-if="versionDoc" class="overlay" @click.self="!adminBusy && (versionDoc=null)">
    <section class="modal" role="dialog" aria-modal="true" aria-label="版本历史">
      <div class="modal-heading"><h2>版本历史 · {{versionDoc.filename}}</h2><button :disabled="adminBusy" @click="versionDoc=null">关闭</button></div>
      <p>只有解析、索引完成且审核通过的版本可以切换为有效版本。</p>
      <div class="table-wrap"><table><thead><tr><th>版本</th><th>处理</th><th>审核</th><th>当前选择</th><th>操作</th></tr></thead><tbody><tr v-for="v in versions" :key="v.version_id"><td>v{{v.version}}</td><td>{{v.status}} / {{v.index_status}}</td><td>{{v.review_status}}</td><td>{{v.is_current?'是':'否'}}</td><td><button v-if="canWriteKb" :disabled="adminBusy||v.is_current||v.status!=='parsed'||v.index_status!=='indexed'||v.review_status!=='approved'" @click="publishVersion(v)">设为有效版本</button></td></tr></tbody></table></div>
    </section>
  </div>
  <div v-if="deleteDoc" class="overlay" @click.self="!adminBusy && (deleteDoc=null)">
    <form class="modal" role="dialog" aria-modal="true" aria-label="删除文档" @submit.prevent="confirmDeleteDoc">
      <h2>删除文档</h2><p>将永久删除「{{deleteDoc.filename}}」的全部版本、切片、向量和未共享文件，无法恢复。知识库、其他文档、审计与历史反馈保留。</p>
      <label>输入完整文件名确认<input v-model="deleteDocName" aria-label="删除文档确认文件名" :disabled="adminBusy" maxlength="255"></label>
      <div class="modal-actions"><button class="primary" :disabled="adminBusy||deleteDocName!==deleteDoc.filename">确认永久删除</button><button type="button" :disabled="adminBusy" @click="deleteDoc=null">取消</button></div>
    </form>
  </div>

  <div v-if="passwordUser" class="overlay" @click.self="!adminBusy && (passwordUser=null)"><form class="modal" role="dialog" aria-modal="true" aria-label="设置成员密码" @submit.prevent="resetUserPassword">
    <h2>设置密码 · {{passwordUser.email}}</h2><p>设置后该成员所有旧 Token 将失效，需要重新登录。</p>
    <label>新密码<input v-model="adminPassword" type="password" required minlength="8" autocomplete="new-password" aria-label="成员新密码"></label>
    <label>确认新密码<input v-model="adminPasswordConfirm" type="password" required autocomplete="new-password" aria-label="成员确认新密码"></label>
    <div class="modal-actions"><button class="primary" :disabled="adminBusy||!adminPassword||adminPassword!==adminPasswordConfirm">保存密码</button><button type="button" :disabled="adminBusy" @click="passwordUser=null;adminPassword='';adminPasswordConfirm=''">取消</button></div>
  </form></div>
  <!-- ================= 安全设置 ================= -->
  <div v-if="showSecurity" class="overlay" @click.self="showSecurity=false">
    <section role="dialog" aria-modal="true" aria-label="安全设置" class="modal">
      <div class="modal-heading"><h2>安全设置</h2><button type="button" class="icon" @click="showSecurity=false" aria-label="关闭">×</button></div>
      <p>{{me.email}} · {{roleLabel}}<template v-if="me.is_platform_admin"> · 平台管理员</template><template v-else-if="me.tenant_id"> · 租户 {{me.tenant_id}}</template></p>
      <div v-if="securityError" class="alert error">{{securityError}}</div>
      <div v-if="securityNotice" class="alert">{{securityNotice}}</div>

      <section class="security-block">
        <h3>修改密码</h3>
        <p>至少 8 位，需同时包含字母与数字；不能与最近用过的密码重复。</p>
        <form @submit.prevent="changePassword">
          <label>当前密码<input v-model="pwForm.current_password" type="password" autocomplete="current-password" required></label>
          <label>新密码<input v-model="pwForm.new_password" type="password" autocomplete="new-password" required></label>
          <button class="primary" :disabled="busySecurity||!pwForm.current_password||!pwForm.new_password">{{busySecurity?'提交中…':'更新密码'}}</button>
        </form>
      </section>

      <section class="security-block">
        <h3>二次验证 <span class="badge" :class="{ready:me.totp_enabled}">{{me.totp_enabled?'已开启':'未开启'}}</span></h3>
        <p v-if="me.totp_enabled">登录时需要输入认证器上的 6 位动态验证码；关闭同样需要一次有效验证码。</p>
        <p v-else>用 Google Authenticator / 1Password 等认证器录入下面的密钥，再输入验证码即可开启。</p>
        <template v-if="!me.totp_enabled">
          <button v-if="!totpSecret" type="button" class="ghost" :disabled="busySecurity" @click="startTotp">{{busySecurity?'生成中…':'开始设置'}}</button>
          <template v-else>
            <div class="secret-box">
              <small>密钥（手动录入）</small>
              <div class="secret-value">{{totpSecret}}</div>
              <small>或使用此链接添加：</small>
              <code>{{totpUri}}</code>
            </div>
            <form class="inline-form" @submit.prevent="enableTotp">
              <input v-model="totpCode" inputmode="numeric" placeholder="6 位验证码" aria-label="验证码" maxlength="16">
              <button class="primary" :disabled="busySecurity||!totpCode.trim()">开启二次验证</button>
            </form>
          </template>
        </template>
        <form v-else class="inline-form" @submit.prevent="disableTotp">
          <input v-model="totpCode" inputmode="numeric" placeholder="6 位验证码" aria-label="验证码" maxlength="16">
          <button class="ghost" :disabled="busySecurity||!totpCode.trim()">关闭二次验证</button>
        </form>
      </section>

      <section class="security-block">
        <h3>会话</h3>
        <p v-if="me.local">当前是本机免鉴权空间，没有登录会话（可通过环境变量 <code>AUTH_MODE=enforced</code> 启用鉴权）。</p>
        <p v-else>退出会吊销当前 Token；若通过企业 SSO 登录，会同时结束提供方会话。</p>
        <button type="button" class="ghost" @click="showSecurity=false; signOut()">退出登录</button>
      </section>
    </section>
  </div>

  <!-- ================= 既有弹层 ================= -->
  <div v-if="showCreate" class="overlay" @click.self="showCreate=false">
    <form role="dialog" aria-modal="true" aria-label="创建知识库" class="modal" @submit.prevent="create">
      <div class="modal-heading"><h2>创建知识库</h2><button type="button" class="icon" @click="showCreate=false" aria-label="关闭">×</button></div>
      <p>按团队或主题整理资料。统一问答会检索你有权访问的全部知识库，也可选择单个知识库提问。</p>
      <label>知识库名称<input v-model="name" required maxlength="128" placeholder="例如：IT 运维知识库"></label>
      <label>描述（可选）<textarea v-model="description" maxlength="512" placeholder="这里保存哪些资料？"></textarea></label>
      <button class="primary" :disabled="creating||!name.trim()">{{creating?'创建中…':'创建知识库'}}</button>
    </form>
  </div>

  <div v-if="kbAction" class="overlay" @click.self="!adminBusy && (kbAction=null)">
    <form class="modal" role="dialog" aria-modal="true" :aria-label="kbAction.kind==='rename'?'知识库改名':'删除知识库'" @submit.prevent="submitKbAction">
      <div class="modal-heading"><h2>{{kbAction.kind==='rename'?'知识库改名':'删除知识库'}}</h2><button type="button" class="icon" :disabled="adminBusy" @click="kbAction=null" aria-label="关闭">×</button></div>
      <template v-if="kbAction.kind==='rename'"><label>新名称<input v-model="kbName" maxlength="128" required aria-label="知识库新名称" :disabled="adminBusy"></label></template>
      <template v-else><p>将永久删除「{{kbAction.name}}」及其文档、版本、切片、向量、成员关系和相关反馈，无法恢复。操作与历史审计将保留。</p><label>输入知识库完整名称确认<input v-model="kbConfirmation" maxlength="128" required aria-label="删除确认名称" :disabled="adminBusy" autocomplete="off"></label><p>解析或索引任务尚未结束时，请等待后重试。</p></template>
      <p v-if="error" role="alert">{{error}}</p>
      <button class="primary" :disabled="adminBusy || (kbAction.kind==='rename'?!kbName.trim():kbConfirmation!==kbAction.name)">{{adminBusy?'处理中…':kbAction.kind==='rename'?'保存名称':'确认永久删除'}}</button>
      <button type="button" class="text-button" :disabled="adminBusy" @click="kbAction=null">取消</button>
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
            <tr v-for="m in members" :key="m.user_id"><td>{{m.display_name || m.email}}<small v-if="m.display_name && m.display_name !== m.email">{{m.email}}</small></td><td><span class="badge">{{m.role}}</span></td><td><button class="text-button" :disabled="adminBusy" @click="removeMember(m)">移除</button></td></tr>
          </tbody>
        </table>
        <div v-if="!members.length" class="empty">还没有成员记录。</div>
      </div>
    </section>
  </div>

  <div v-if="showReviews" class="overlay" @click.self="showReviews=false">
    <section role="dialog" aria-modal="true" aria-label="待审版本" class="modal wide">
      <div class="modal-heading"><h2>待审版本 · {{kb?.name}}</h2><button type="button" class="icon" @click="showReviews=false" aria-label="关闭">×</button></div>
      <p>审核通过后该版本才会参与检索；提交人不能审核自己提交的版本。</p>
      <label>审核备注（可选）<input v-model="reviewNote" maxlength="512" placeholder="例如：口径与现行制度一致"></label>
      <div class="table-wrap">
        <table>
          <thead><tr><th>文档</th><th>版本</th><th>解析</th><th>提交人 ID</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="v in reviews" :key="v.version_id">
              <td>{{v.filename}}</td>
              <td>v{{v.version}}</td>
              <td><span class="badge">{{v.status}}</span></td>
              <td>{{v.uploaded_by ?? '—'}}</td>
              <td class="row-actions">
                <button class="text-button" :disabled="adminBusy" @click="decideReview(v,'approve')">通过并发布</button>
                <button class="text-button" :disabled="adminBusy" @click="decideReview(v,'reject')">驳回</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!reviews.length" class="empty">当前没有待审版本。</div>
      </div>
    </section>
  </div>
</div>
</template>
