# P0：身份认证与知识库授权

分支 `fix/citation-completeness` 之后的权限工作独立阶段。P0 只做**认证 + 授权执行机制**；
前端登录、成员管理界面、审核发布属于 P1/P2，尚未实现。

## 1. 交付内容

| 文件 | 作用 |
|---|---|
| `app/db/deps.py` | 统一的 `get_db` / `DB`；所有路由（含认证）共用同一个依赖对象，测试一次覆盖即可生效 |
| `app/modules/auth/models.py` | `users`、`api_tokens`、`kb_members` |
| `app/modules/auth/principal.py` | 调用者身份 `Principal`（id/email/role）与本地管理员常量 |
| `app/modules/auth/security.py` | token 生成与 SHA-256 摘要（只存摘要） |
| `app/modules/auth/service.py` | 认证解析与授权规则（唯一授权判定入口） |
| `app/modules/auth/deps.py` | FastAPI 依赖：`current_principal`、`require_admin` |
| `app/modules/knowledge/router.py` | 建库/列表/上传/文档详情/切片/重试全部加授权 |
| `app/modules/retrieval/router.py` | `scope="all"` 改为“授权库集合”；显式越权库 403；索引接口加授权 |
| `app/modules/chat/router.py` | 问答沿用同一条授权路径，不再绕过 |
| `migrations/versions/0004_auth_access.py` | 新增三张表 + `knowledge_bases.owner_id`、`documents.uploaded_by` |
| `scripts/manage_users.py` | 建用户、签发/吊销 token、授予知识库成员、列用户 |
| `tests/test_authz.py` | 14 项负向与作用域测试 |

## 2. 关键语义

- `AUTH_MODE=off`（默认）：所有请求视为**本地管理员**，与历史行为一致，单机开发与旧评测脚本无需改动。
- `AUTH_MODE=enforced`：必须携带 `Authorization: Bearer <token>`，否则 **401**；token 无效/被吊销/用户停用同样 401。
- 已认证但无权访问：**403**。显式请求未授权知识库返回 403，而不是静默返回空结果——
  用户需要知道“有库但没权限”，而不是误以为“资料不足”。代价是会暴露该库存在，属可接受取舍。
- `scope="all"` **不等于全表**：只展开为调用者可读的知识库集合；管理员才等于全部。
- 上传/建库需要全局 `editor` 或 `admin`；知识库内 `owner`/`editor` 可写，`viewer` 只读。
- 建库者自动成为该库 `owner`（写入 `kb_members` + `knowledge_bases.owner_id`）。
- token 为高熵随机串（`knp_` 前缀），数据库只存 SHA-256 摘要；明文仅签发时显示一次。

## 3. 迁移与启用步骤

```bash
cd outputs/knowops
/opt/anaconda3/envs/knowops/bin/alembic upgrade head          # 应用 0004
/opt/anaconda3/envs/knowops/bin/python scripts/manage_users.py \
  create-user --email admin@corp --role admin --token          # 首个管理员，token 只显示一次
/opt/anaconda3/envs/knowops/bin/python scripts/manage_users.py \
  grant-kb --email alice@corp --kb-id 10 --role viewer         # 授权到具体知识库
# 确认无误后再切模式（当前 .env 不含该键，默认 off）
echo 'AUTH_MODE=enforced' >> .env && 重启 API
```

未加入 `kb_members` 的普通用户看不到任何知识库；管理员不受成员表限制。

## 4. 已验证

- `ruff check .` 通过；`pytest` **90 项通过**（原 76 项 + 新增 14 项），既有评测与隔离测试语义未变。
- 真实 MySQL 已应用 0004，新增表与列经 `describe` 核对；`knowledge_bases`/`documents` 无历史数据被改写。
- 临时 8011 端口以 `AUTH_MODE=enforced` 启动真实服务实测：
  无 token/错 token → 401；管理员 token → 200 且返回全部 12 个库；
  仅授权 kb 10 的 viewer：`scope="all"` 只命中 kb 10、显式请求 kb 11 → 403、建库 → 403、
  读 kb 10 文档列表 → 200、读 kb 11 → 403。
- 验证用的临时用户与 token 已从数据库删除（`users`/`api_tokens`/`kb_members` 均为 0 行），临时服务已关闭。
- 8010 上运行的本地服务在 `AUTH_MODE=off` 下健康检查、知识库列表、统一检索均正常。

## 5. 明确未做（后续阶段）

- 前端登录、token 输入、按角色隐藏上传/建库按钮（P1）。
- 成员管理 API 与界面（目前只能用 CLI，P1）。
- 提交→审核→发布流程、审计日志、文档版本更新与下架同步（P2）。
- SSO/OIDC、多租户、按部门继承授权（P3）。
- 未加：登录限流、token 过期时间、管理员操作审计；`last_used_at` 目前每次请求写一次。
- `AUTH_MODE=off` 是单机开发便利开关，**不是生产配置**；生产必须 enforced 并配合前端登录。
