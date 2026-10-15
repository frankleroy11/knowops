# 本地账号密码登录与 Token 生命周期

补齐认证链路上最基础的一组能力：**账号密码登录（P1.5）**、**登录失败锁定**、
**Token 过期与轮换**、**自助登出**。此前只能靠管理员签发 API Token 登录。

## 1. 交付内容

| 文件 | 作用 |
|---|---|
| `app/modules/auth/security.py` | `hashlib.scrypt` 口令散列（每口令独立盐），保持 Token 摘要逻辑不变 |
| `app/modules/auth/models.py` | `users.password_hash`/`failed_logins`/`locked_until`；`api_tokens.expires_at` |
| `app/modules/auth/service.py` | `authenticate_password`（含锁定与恒定开销）、`set_password`/`change_password`、`token_expiry`、`revoke_presented_token`；`resolve_principal` 拒绝过期 Token |
| `app/modules/auth/router.py` | `POST /auth/password/login`、`POST /auth/password`、`POST /auth/logout`、`POST /auth/token/rotate`、`POST /admin/users/{id}/password` |
| `migrations/versions/0008_password_login.py` | 上述字段（纯新增，历史数据不受影响） |
| `scripts/manage_users.py` | `create-user --password`、`set-password`、`issue-token --days`（0 表示不过期） |
| `frontend/src/App.vue` | 登录界面改为「邮箱+密码」为主，API Token 收进折叠项，SSO 按钮保留 |
| `tests/test_password_auth.py` | 14 项 |

## 2. 安全属性

- **口令散列**：`scrypt(n=2^14, r=8, p=1, dklen=32)`，每条口令独立 16 字节盐，
  存储格式 `scrypt$N$r$p$salt$digest`；校验用 `hmac.compare_digest`。不引入新依赖（本机离线）。
- **未知账号与错误口令返回同一提示**（"邮箱或密码不正确"），且未知账号也执行一次 scrypt，
  避免通过响应时间枚举账号。
- **登录失败锁定**：连续失败达到 `LOGIN_MAX_FAILURES`（默认 5）即锁定
  `LOGIN_LOCKOUT_MINUTES`（默认 15）分钟，锁定期内即使口令正确也返回 429；
  成功登录清零计数。注意：**触发锁定的那一次返回 401，下一次才是 429**。
- **Token 过期**：`TOKEN_TTL_DAYS`（默认 30）控制新 Token 有效期，0 表示不过期；
  过期时间由 **API 时钟**写入与比较（避免 P3b 那类数据库/应用时钟不一致问题）。
- **轮换与登出只影响当前这一个 Token**：`/auth/token/rotate` 先吊销请求所用的 Token 再签发新的；
  `/auth/logout` 只吊销请求所用的 Token，其他设备上的会话不受影响。
- 管理员重置口令需要管理员权限，且**只能操作本租户用户**（平台管理员不受限），并写审计。

## 3. 配置

```env
TOKEN_TTL_DAYS=30          # 0 = 不过期
PASSWORD_MIN_LENGTH=8
LOGIN_MAX_FAILURES=5
LOGIN_LOCKOUT_MINUTES=15
```

以上能力**仅在 `AUTH_MODE=enforced` 下可用**：本地免鉴权模式（`off`）调用
`/auth/password/login` 返回 404，避免出现"能登录但 Token 不生效"的错觉。

## 4. 命令行

```bash
python scripts/manage_users.py create-user --email alice@corp --role editor --tenant default --password 'S3cret!pass'
python scripts/manage_users.py set-password --email alice@corp --password 'NewS3cret!'
python scripts/manage_users.py issue-token --email alice@corp --days 7     # 0 = 不过期
```

## 5. 验证

- `ruff check .` 通过；`pytest` **159 项通过**（此前 145 项 + 本阶段 14 项）；前端生产构建通过。
- 迁移 0008 已应用到真实 MySQL，`describe` 确认新增列存在；off 模式行为不变
  （`/auth/me` 仍是本地平台管理员，密码登录 404）。
- **真实 MySQL 端到端验收**（临时 8011、`AUTH_MODE=enforced`）：密码登录签发 Token 且可访问
  `/auth/me`；错误口令与未知账号均 401 且提示一致；`--days -1` 的 Token 401（过期）、
  `--days 0` 的 Token 200（不过期）；轮换后旧 Token 401、新 Token 200；登出吊销当前 Token（其余会话不受影响）；
  管理员重置口令后旧口令失效、新口令可登录；自助修改口令与最小长度 422 校验；
  锁定阈值 5 次 → 第 6 次 429、锁定期内正确口令仍 429。验收数据已全部清理（0 用户/0 Token/0 审计）。
- 前端：`/ui/` 提供的构建产物包含密码登录调用（`auth/password/login`）与「改用 API Token 登录」入口。
  仍未做浏览器视觉验收（本机 Chrome headless 不可用）。

## 6. 未做（列表中的其余项）

- **JWKS 缓存与 `kid` 轮换刷新**（OIDC 侧，当前每次登录拉取一次）。
- **IdP 组/角色声明 → 本地角色映射**（当前用固定默认角色或既有账号角色）。
- **审计日志按租户分区**（当前仅平台管理员可读，租户管理员看不到本租户审计）。
- **前端租户管理界面**（当前租户只能用 API / CLI 管理）。
- 本阶段自身未做：忘记密码自助重置（需邮件通道）、口令历史与复杂度策略、
  按 IP/设备限流（当前仅按账号锁定）、二次验证。
