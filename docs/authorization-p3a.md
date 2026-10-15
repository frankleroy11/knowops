# P3a：多租户隔离

P3 分两步：**P3a 多租户**（本文）与 **P3b SSO/OIDC**（待做）。
本机离线且未安装 PyJWT，P3b 的 ID Token 验签将用已有的 `cryptography` 自行实现。

## 1. 交付内容

| 文件 | 作用 |
|---|---|
| `app/modules/tenant/models.py`、`service.py`、`router.py` | 租户表与查询；平台管理员专用 `GET/POST /admin/tenants` |
| `migrations/versions/0006_tenants.py` | `tenants` 表；`users.tenant_id`（NULL＝平台级）、`knowledge_bases.tenant_id`（NOT NULL）；历史数据回填到 `default` 租户 |
| `app/modules/auth/principal.py` | `Principal.tenant_id` 与 `is_platform_admin`（admin 且无租户） |
| `app/modules/auth/service.py` | 授权全部按租户收敛：`authorized_kb_ids`、`has_tenant_access`、`kb_permission`、`require_kb`、`membership_roles`、`kb_role` |
| `app/modules/auth/router.py` | `/auth/me` 暴露 `tenant_id`/`is_platform_admin`；用户列表/建用户/改角色/签发吊销 Token 全部按调用者租户收敛；仅平台管理员可改用户租户 |
| `app/modules/knowledge/router.py` | 建库落到调用者租户（平台管理员可指定）；跨租户成员授予按 404 隐藏 |
| `app/modules/audit/router.py` | 审计日志改为**仅平台管理员**可读 |
| `scripts/manage_users.py` | `create-tenant`、`create-user --tenant/--platform`；CLI 的所有变更操作补写审计（actor `cli@localhost`） |
| `frontend/src/App.vue` | 侧边栏显示租户/平台身份；审计入口仅平台管理员可见 |
| `tests/test_tenancy.py` | 11 项隔离与越权测试 |

## 2. 关键语义

- **两级管理员**：
  - 平台管理员 = `role=admin` 且 `tenant_id IS NULL` → 可管理所有租户、所有知识库、审计日志；
  - 租户管理员 = `role=admin` 且属于某租户 → 管理**本租户**全部知识库与用户，不能建租户、不能读全平台审计、不能把用户移出租户。
- **普通成员**：只能看到自己被授予成员关系的**本租户**知识库。
- **跨租户一律 404**（隐藏存在性），**同租户无权限才 403**（用户已知该库存在）。
- `scope="all"` 对所有角色都只展开为**本租户**可读集合；平台管理员才等于全平台。
- 跨租户成员授予、跨租户用户管理、跨租户 Token 操作均按 404 处理。
- `AUTH_MODE=off` 下的本地管理员即平台管理员，**本机单用户行为不变**。

## 3. 验证

- `ruff check .` 通过；`pytest` **130 项通过**（P2 的 119 项 + 本阶段 11 项）；前端生产构建通过。
- 迁移 0006 已应用到真实 MySQL：新建 `default` 租户，12 个历史知识库全部归入该租户，
  用户数 0；`/auth/me` 在 off 模式下报 `tenant_id=null, is_platform_admin=true`。
- **真实端到端验收 12/12 通过**（临时 8011 以 `AUTH_MODE=enforced` 运行，真实 MySQL）：
  平台管理员建租户与用户 → 租户 1/2 管理员各自只看到本租户知识库 → 平台管理员可跨租户建库 →
  跨租户检索/文档列表/成员授予全部 404 → 租户管理员用户列表仅本租户 → 租户管理员读审计 403、
  平台管理员读审计 200 → CLI 操作留有审计记录。
- 验收后数据库回到验收前（1 租户、12 知识库、0 用户、0 审计）。

## 4. 验证中发现并修复的问题

1. **跨租户审计泄露**：审计日志原本对所有管理员开放，租户管理员会读到其他租户的操作记录。
   由于 `audit_logs` 尚无按租户分区，已改为**仅平台管理员可读**（fail-closed），
   并在 UI 中同步隐藏入口。按租户分区留待后续（需要新增 `audit_logs.tenant_id`）。
2. **CLI 操作不留痕**：`scripts/manage_users.py` 直接写库、绕过审计，导致“谁建了租户/发了 Token”无记录。
   已为 CLI 的全部变更操作补写审计（actor 记为 `cli@localhost`），并在验收中覆盖。

## 5. 未做（P3b 及之后）

- **SSO/OIDC**：授权码流程、JWKS 验签（用 `cryptography` 实现 RS256）、账号自动开通与绑定、
  `state`/`nonce` 校验；计划用本地假 IdP + `httpx.MockTransport` 做离线测试。
- 按租户分区的审计日志与合规导出。
- 前端租户管理界面（当前仅 API + CLI）。
- 用户名+密码登录、Token 过期与轮换、登录限流。
