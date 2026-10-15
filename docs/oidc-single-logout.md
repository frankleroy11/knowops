# SSO 单点登出（RP-initiated logout）

接续 [P3b 单点登录](authorization-p3b.md) 与 [OIDC 增强](oidc-jwks-and-role-mapping.md)。
此前只有本地 Token 吊销，SSO 会话仍留在 IdP 侧；本阶段把两侧都闭合。

## 1. 交付内容

| 位置 | 作用 |
|---|---|
| `GET /auth/oidc/logout` | 302 跳转到 IdP 的 `end_session_endpoint`，带 `client_id` 与**绝对地址**的 `post_logout_redirect_uri`；`?web=false` 时返回 `{"logout_url": ...}` 供 API 客户端使用 |
| `OIDC_POST_LOGOUT_REDIRECT` | 登出回跳地址，可填绝对 URL；留空则用 `OIDC_WEB_REDIRECT`（默认 `/ui/`）并**按 `OIDC_REDIRECT_URI` 推导同源绝对地址** |
| `POST /auth/logout`（已有） | 先吊销本地 Token，现在同时写审计 `auth.logout` |
| `frontend/src/App.vue` | 记录登录方式（`localStorage: knowops.login_method`）；退出时先本地吊销，若本次是 SSO 登录且启用 SSO，再跳转 `/auth/oidc/logout` 结束 IdP 会话 |
| `scripts/dev_fake_idp.py` | 假 IdP 增加 `end_session_endpoint` 与 `/logout` 回跳端点，便于本地联调 |
| `tests/test_oidc.py`、`tests/test_password_auth.py` | 新增 5 项（登出跳转、JSON 模式、提供方不支持时 404、回跳地址可覆盖且保持绝对、Web 回调记录登录方式、登出审计） |

## 2. 关键语义

- 两个动作分开、语义清晰：**本地吊销**用 `POST /auth/logout`（带 Token 头，浏览器导航做不到），
  **IdP 会话结束**用 `GET /auth/oidc/logout`（浏览器跳转）。前端先前者再后者。
- `post_logout_redirect_uri` 必须是**绝对 URI**：只配置路径时，服务端按已注册的
  `OIDC_REDIRECT_URI` 的 scheme+host 拼出绝对地址；显式配置绝对 URL 时原样使用。
- 提供方元数据没有 `end_session_endpoint` 时返回 404（"未声明 end_session_endpoint"），
  不静默跳到错误地址。
- 登出只吊销**当前这一个** Token，其他设备会话不受影响。

## 3. 验证

- `ruff check .` 通过；`pytest` **172 项通过**（本轮 +6）；前端生产构建通过。
- **真实 HTTP 端到端**（假 IdP + `AUTH_MODE=enforced` 的 API）：
  SSO 登录拿到 Token → `/auth/me` 200 → `POST /auth/logout` 返回 `revoked=1`、原 Token 立即 401 →
  `GET /auth/oidc/logout` 302 到
  `http://127.0.0.1:8020/logout?client_id=knowops-dev&post_logout_redirect_uri=http%3A%2F%2F127.0.0.1%3A8011%2Fui%2F`
  → **跟随整条链路最终回到本应用 `/ui/` 并返回 200**（说明绝对回跳地址生效）→
  再次 SSO 登录成功（复用同一账号）→ 审计依次记录 `user.oidc.provision`、`auth.oidc.login`、`auth.logout`（可重复）。
- 验收数据全部清理（0 用户/0 Token/0 审计/0 登录状态/12 知识库）。

## 4. 验证中发现并修复的问题

**`post_logout_redirect_uri` 用了相对路径 `/ui/`**：真实 IdP 要求绝对 URI，否则会拒绝或跳到错误位置
（本地假 IdP 直接把它当作 IdP 自身路径，跟随链路落到 `http://127.0.0.1:8020/ui/` 404）。
已改为按 `OIDC_REDIRECT_URI` 的 scheme+host 推导绝对地址，并加测试固定该行为。

## 5. 仍未做

- 忘记密码自助重置（需邮件通道）、按 IP/设备限流、二次验证。
- IdP 侧 `id_token_hint`（当前不保存 ID Token）与刷新令牌。
- 审计日志合规导出与保留策略。
