# 账号安全：口令策略、按 IP 限流、二次验证、自助重置、审计导出与保留

对应"认证与权限侧未做"清单的第 6–13 项，一次做完（迁移 `0011`）。

## 1. 口令策略与历史（#9）

`validate_password()` 现在检查：长度（`PASSWORD_MIN_LENGTH`）、**字母+数字混合**、不能包含邮箱名、
不能是常见弱口令（内置列表）、**不能与最近 N 次用过的口令重复**（`PASSWORD_HISTORY_SIZE`，默认 5）。

- 新表 `password_history` 只存摘要（scrypt），改口令时把旧摘要记入，并只保留最近 N 条；
- 管理员重置口令（`POST /admin/users/{id}/password`）与自助重置走同一套校验。

## 2. 按来源 IP 限流（#7）

`login_attempts` 表记录失败尝试，`enforce_ip_rate_limit()` 用**滑动窗口**判断：
`LOGIN_ATTEMPT_WINDOW_MINUTES`（默认 10 分钟）内同一 IP 失败 ≥ `LOGIN_ATTEMPTS_PER_IP`（默认 20）→ **429**。
它与已有的账号级锁定互补：账号锁定防单账号爆破，IP 限流防撞库。

**一个刻意的取舍**：成功登录会清掉该 IP 的失败记录。企业内网常见多人共用一个出口 IP，
不清零会让几次输错口令把整个出口锁到窗口结束。代价是"攻击者已掌握一个有效账号时可通过
成功登录重置该 IP 计数"——但那时已不属于盲撞库场景。这条取舍写进了代码注释与测试。

## 3. 二次验证 TOTP（#8）

用标准库自实现 RFC 6238（HMAC-SHA1 / 30 秒步长 / 6 位），**并用 RFC 附录 B 的官方向量做单测**
（`totp_code(secret, at=59) == "287082"` 等），不引入第三方依赖。

| 接口 | 说明 |
|---|---|
| `POST /auth/2fa/setup` | 生成密钥与 `otpauth://` 链接（此时**尚未启用**） |
| `POST /auth/2fa/enable` | 用一次有效验证码确认后才真正启用 |
| `POST /auth/2fa/disable` | 同样需要有效验证码 |
| `POST /auth/password/login` | 启用后必须带 `code`；缺失返回 401"需要二次验证码" |
| `GET /auth/me` | 新增 `totp_enabled` |

允许前后各 1 个时间步（`TOTP_WINDOW`），避免客户端时钟轻微偏差导致登录失败。
密钥以明文存于 `users.totp_secret`——数据库本身已是信任边界；如需加密列可后续加。

## 4. 自助重置口令（#6）

未接邮件通道，因此做成"**令牌 + 管理员/CLI 转交**"：

- `POST /auth/password/forgot`：**统一返回 202**（不暴露邮箱是否存在）。
  仅在 `AUTH_DEV_REVEAL_RESET_TOKEN=true` 的本地调试模式下才在响应里直接给令牌；
- `scripts/manage_users.py reset-token --email X [--ttl-minutes N]`：管理员生成令牌转交用户；
- `POST /auth/password/reset {token, new_password}`：一次性、限时（默认 30 分钟），
  成功后**吊销该用户所有旧 Token**（要求重新登录），并写审计。

## 5. 登出联动与 ID Token（#10）

SSO 登录时把 ID Token 存到本地 Token 行（`api_tokens.id_token`，仅用于登出提示）；
`POST /auth/logout` 现在返回 `{"revoked", "oidc_logout_url"}`，
其中地址带 `id_token_hint`（best-effort：发现失败不影响本地登出）。
前端登出优先跳这个地址，**本地密码登录不再被跳去 IdP**。

**刷新令牌仍然不做**：本方案直接签发本地 API Token（TTL 可控 + 可轮换 + 可吊销），
比引入 refresh token 链路更简单，也少一份泄露面。这一条从 P3b 起就是明确取舍。

## 6. 登录状态清理（#11）

`prune_login_states()` 删除已消费或超过 `ttl_minutes` 的 `oidc_login_states` 行，
在每次 OIDC 登录开始时顺手调用（幂等、有界），不再让表无限增长。

## 7. 审计导出与保留（#12）

- `GET /admin/audit-logs/export?format=csv|json`：合规导出，范围规则与列表接口一致
  （平台管理员可跨租户，租户管理员只看本租户）；CSV 带 `Content-Disposition` 便于归档。
- `scripts/prune_audit_logs.py --days 180 [--delete]`：默认只统计，确认后才删除。

## 8. 第三个时钟错配 bug（值得记住）

写"按 IP 限流"的单测时发现：`login_attempts.created_at` 用数据库默认值（容器内 UTC），
而限流窗口用 API 时钟（本地 UTC+8）计算 → 计数永远是 0，**限流形同虚设**。
这是同类问题的第三次（前面是 OIDC 登录状态、审计时间戳）。现在统一为：**凡是参与时间比较的时间戳，
一律由 API 时钟显式写入**，并各配一条"时间戳必须接近当前时间"的回归测试。

## 9. 验证

- `ruff check .` 通过；`pytest` **215 项通过**（新增 18 项：账号安全 16 + SSO 登出提示 2）；
  前端 `node --test` 16 项通过、构建通过。
- 迁移 `0011` 已应用到真实 MySQL（`password_history`/`password_resets`/`login_attempts`
  与 `users.totp_*`、`api_tokens.id_token` 均确认存在）。
- **真实链路验收 25/25**（临时 8011 + 真实 MySQL）：口令策略拒绝、2FA 全流程
  （含登录被挡/放行、停用需验证码）、4 次失败后第 5 次 429、成功后清零、自助重置
  （202/一次性/吊销旧 Token/旧口令失效）、审计 CSV+JSON 导出与保留脚本、本地登录登出无 IdP 提示。
- 验收数据已清理：用户 0、知识库 12、尝试 0、历史 0、重置 0、审计 0。

## 10. 仍未做

- **真实邮件通道**（SMTP/企业邮箱）——目前令牌靠 CLI/管理员转交；
- **TOTP 恢复码**、短信/WebAuthn 等其它二次因子；
- **前端安全设置界面**（2FA 绑定、改口令、自助重置目前只有 API 与 CLI）；
- 审计导出的分页/大表流式下载与压缩（当前一次最多 5000 行）；
- IP 白名单/黑名单策略、按设备的会话管理界面。
