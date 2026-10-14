# OIDC 增强：JWKS 缓存与密钥轮换、IdP 组到角色的映射

接续 [P3b 单点登录](authorization-p3b.md)。这两项补上了当时明确留下的缺口。

## 1. JWKS 缓存与 `kid` 轮换

- `app/modules/oidc/client.py` 新增进程内 JWKS 缓存：`{jwks_uri: (fetched_at, keys)}`，TTL 由
  `OIDC_JWKS_TTL_SECONDS`（默认 600 秒）控制；`jwks(uri, refresh=True)` 强制刷新；
  `reset_jwks_cache()` 供测试与运维使用。
- `app/modules/oidc/tokens.py` 新增 `UnknownKeyError`（`TokenError` 的子类），
  仅当"token 里的 `kid` 在现有 JWKS 中找不到"时抛出。
- `app/modules/oidc/service.py` 首次验签遇到 `UnknownKeyError` 时**强制刷新一次 JWKS 再试一次**，
  这正好覆盖提供方轮换签名密钥的场景；其他校验失败（签名错、受众错、过期、nonce 不符）不会重试。
- 效果：正常登录不再每次拉取 JWKS；轮换后第一次登录自动恢复，无需重启服务。

## 2. IdP 组到本地角色的映射

- 配置：
  - `OIDC_ROLE_CLAIM`（默认 `groups`）：从 ID Token 的哪个声明读取组，支持字符串或数组。
  - `OIDC_ROLE_MAP`（默认空）：JSON 映射，如 `{"knowops-admins": "admin", "knowops-editors": "editor"}`，
    按映射书写顺序取第一个命中的合法角色（`admin`/`editor`/`viewer`）。
  - `OIDC_ROLE_SYNC`（默认 `false`）：是否在**每次登录**按映射同步既有账号的角色。
- 语义：
  - **新开通账号**：映射命中则用映射角色，否则用 `OIDC_DEFAULT_ROLE`。
  - **既有账号**：默认**只做账号绑定、不改角色**（避免 IdP 配置变更静默提权/降权）；
    开启 `OIDC_ROLE_SYNC` 后才同步，并写审计 `user.oidc.role`。
  - 映射缺失、JSON 非法、或映射值不是合法角色 → 一律回退到默认角色，不报错中断登录。

## 3. 验证

- `ruff check .` 通过；`pytest` **166 项通过**（新增 6 项）；前端生产构建通过。
- 新增单元/集成测试：两次登录只拉取一次 JWKS；`OIDC_JWKS_TTL_SECONDS=0` 时每次重取；
  **`kid` 轮换后自动刷新且只刷新一次**（假 IdP 切换 `kid=rotated`）；组声明映射到 `admin`；
  映射缺失/JSON 非法/角色非法三种情况均回退默认角色；既有账号在 `OIDC_ROLE_SYNC=false` 时角色不变、
  开启后同步为映射角色并留审计。
- **真实 HTTP 验收**：假 IdP 返回 `groups=["knowops-editors"]`，配合
  `OIDC_ROLE_MAP={"knowops-editors":"editor"}` → 新开通账号角色直接是 `editor`；
  随后用 `--rotate` 重启假 IdP（新密钥 + `kid=rotated`）再次登录 → **登录成功**（说明缓存 JWKS 因未知 `kid`
  被刷新并重试），且复用同一本地账号、角色未被静默改动。验收数据已清理（0 用户/0 Token/0 审计/0 登录状态）。
- `scripts/dev_fake_idp.py` 增加 `--groups` 与 `--rotate`，供后续本地联调复现。

## 4. 仍未做

- 忘记密码自助重置（需邮件通道）、按 IP/设备限流、二次验证。
- IdP 侧登出联动（RP-initiated logout）与刷新令牌。
- 审计日志的合规导出与保留策略。
