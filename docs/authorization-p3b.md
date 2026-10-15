# P3b：SSO/OIDC 单点登录

接续 [P3a 多租户](authorization-p3a.md)。本阶段实现授权码登录，并在离线环境下用本地假 IdP
完成真实 HTTP 端到端验收。

## 1. 交付内容

| 文件 | 作用 |
|---|---|
| `app/modules/oidc/tokens.py` | 无第三方依赖的 ID Token 校验：RS256/384/512 验签 + `iss`/`aud`/`exp`/`nbf`/`nonce` 断言 |
| `app/modules/oidc/client.py` | OIDC 发现（`.well-known/openid-configuration`）、JWKS 获取、授权码交换（`client_secret_basic`） |
| `app/modules/oidc/models.py` | `oidc_login_states`：`state`/`nonce`/`web`/`created_at`/`consumed_at` |
| `app/modules/oidc/service.py` | 登录状态创建与消费、账号绑定/自动开通、Web 回调 HTML |
| `app/modules/oidc/router.py` | `GET /auth/oidc/status`、`GET /auth/oidc/start`、`GET /auth/oidc/callback` |
| `migrations/versions/0007_oidc.py` | `oidc_login_states` 表；`users.oidc_issuer`/`oidc_subject`（唯一约束） |
| `scripts/dev_fake_idp.py` | 本地假 IdP（仅联调用，**禁止用于生产**） |
| `frontend/src/App.vue` | 登录界面在 OIDC 启用时显示「使用企业 SSO 登录」 |

> 本机离线且没有 PyJWT/python-jose，因此验签用已安装的 `cryptography` 实现，并通过
> `/auth/oidc/status` 让前端在**未登录状态**下也能知道是否提供 SSO。

## 2. 安全属性

- **只接受 RSA 签名**：`alg` 为 `none` 或 `HS*` 一律拒绝（防算法混淆攻击）。
- **nonce 绑定服务端状态**：`nonce` 由服务端生成并随 `state` 落库，回调时同时校验，
  避免 ID Token 重放。
- **state 单次使用**：`oidc_login_states` 记录 `consumed_at`，重放或未知 state → 400；
  超过 10 分钟 → 400；**交换失败也会消费该 state**（宁可让用户重来，也不给重放留窗口）。
- 校验 `iss`、`aud`（含数组形式）、`exp`、`nbf`，允许可配置时钟偏移（`OIDC_CLOCK_SKEW`，默认 60s）。
- **要求 `email_verified`**：未验证邮箱不允许自动开通；**不做静默身份合并**——
  邮箱已被另一个 sub 绑定时返回 401。
- 自动开通使用配置的默认角色与默认租户（`OIDC_DEFAULT_ROLE`、`OIDC_DEFAULT_TENANT_SLUG`），
  既有本地账号被绑定时**保留其原角色与租户**。
- 登录与开通均写审计：`auth.oidc.login`、`user.oidc.provision`、`user.oidc.link`。
- Web 回调把本地 Token 写入 `localStorage`（键 `knowops.token`）后跳转 `/ui/`，
  **Token 不出现在 URL/浏览器历史里**。

## 3. 配置

```env
OIDC_ENABLED=true
OIDC_ISSUER=https://idp.example.com
OIDC_CLIENT_ID=knowops
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=http://127.0.0.1:8010/api/v1/auth/oidc/callback
OIDC_SCOPES="openid email profile"
OIDC_DEFAULT_ROLE=viewer
OIDC_DEFAULT_TENANT_SLUG=default
OIDC_WEB_REDIRECT=/ui/
```

本地联调：

```bash
python scripts/dev_fake_idp.py --port 8020
AUTH_MODE=enforced OIDC_ENABLED=true OIDC_ISSUER=http://127.0.0.1:8020 \
  OIDC_CLIENT_ID=knowops-dev OIDC_CLIENT_SECRET=dev-secret \
  OIDC_REDIRECT_URI=http://127.0.0.1:8011/api/v1/auth/oidc/callback \
  python -m uvicorn app.main:app --port 8011
```

## 4. 验证

- `ruff check .` 通过；`pytest` **145 项通过**（P3a 的 130 项 + 本阶段 15 项）；前端生产构建通过。
- 单元/集成测试使用**本地假 IdP + `httpx.MockTransport`**（自带 RSA 密钥，离线可跑），覆盖：
  未启用 404、`start` 重定向参数（client_id/redirect_uri/scope/state/nonce）、
  完整登录并签发可用 Token、二次登录复用同一账号、既有本地账号按已验证邮箱绑定且保留角色、
  邮箱已绑其他 sub → 401、未验证邮箱 → 401、state 重放 → 400、未知 state → 400、
  缺授权码 → 400、`error=` 回调 → 401、签名错误/`nonce` 不符/受众不符/已过期 → 401、
  授权码交换失败 → 401、Web 回调返回写 localStorage 的 HTML、`none`/`HS256` 算法被拒、
  **登录状态使用 API 时钟**。
- **真实 HTTP 端到端验收通过**：启动 `scripts/dev_fake_idp.py`（8020）与启用 OIDC 的 API（8011），
  `curl -L` 跟随 302 完成 `start → authorize → callback`：拿到本地 Token → `/auth/me` 显示自动开通的
  `sso@dev.local`（viewer，租户 1）→ 二次登录复用同一账号（id 不变）→ 数据库确认
  `oidc_issuer`/`oidc_subject` 已绑定、审计含 `user.oidc.provision` 与两条 `auth.oidc.login` →
  `web=true` 返回写入 Token 的 HTML → 重放同一 state 返回 400。
- 验收后临时用户/Token/审计/登录状态全部删除（均为 0 行），两个临时服务已关闭。

## 5. 验证中发现并修复的问题

1. **登录状态被误判过期（真实缺陷）**：`created_at` 由数据库 `NOW()` 生成（Docker 里的 MySQL 是 UTC），
   而过期判断用应用本地时钟（UTC+8），导致**每一个新建登录状态立刻被判为过期**，OIDC 登录在生产不可用。
   修复：创建时用 API 进程时钟显式写入 `created_at`，保证比较双方同源；
   并新增回归测试断言「登录状态时间戳与当前时间相差 < 60s」。
2. **测试侧**：本环境的 `TestClient` 默认跟随重定向，`302` 会被跟到假 IdP 路径而返回 404，
   掩盖了真实状态码。已改为 `follow_redirects=False` 并断言真实 302 与 `Location`。

## 6. 未做（后续）

- JWKS 缓存与 `kid` 轮换刷新（当前每次登录拉取一次，量小但可优化）。
- 按 IdP 组/角色声明映射本地角色（当前用固定默认角色或既有账号角色）。
- RP-initiated logout、会话登出联动；刷新令牌（本方案直接签发本地 API Token）。
- `oidc_login_states` 定期清理（过期行目前只标记 `consumed_at`，未物理删除）。
- 前端仅在登录遮罩层提供跳转式 SSO；未做静默续期与多 IdP 选择。
