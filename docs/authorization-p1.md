# P1：角色与知识库 ACL 管理 + 前端按角色呈现

接续 [P0 认证与授权](authorization-p0.md)。本阶段补齐**管理能力**与**前端界面**，默认模式仍为
`AUTH_MODE=off`（单机本地管理员），生产切换步骤见第 5 节。

## 1. 交付内容

| 文件 | 作用 |
|---|---|
| `app/modules/auth/router.py` | `GET /auth/me`；管理员用户管理：列表、创建（可同时签发 Token）、改角色/启停、签发与吊销 Token |
| `app/modules/auth/service.py` | 新增 `membership_roles`、`list_members`、`owner_count`、`remove_membership`、`set_user_role`、`set_user_active`、`admin_count`、`active_token_count` |
| `app/modules/knowledge/router.py` | `GET/POST /knowledge-bases/{id}/members`、`DELETE .../members/{user_id}`；`KBOut.my_role` |
| `frontend/src/App.vue` | 登录覆盖层、身份与角色显示、按权限隐藏操作、用户管理面板、成员权限面板 |
| `frontend/src/style.css` | 上述面板的样式（`.modal.wide`、`.inline-form`、`.token-callout` 等） |
| `tests/test_authz_admin.py` | 14 项身份、用户管理、成员管理与最后管理员/最后 owner 保护测试 |

## 2. 权限矩阵

| 操作 | admin | editor | KB owner | KB editor | KB viewer |
|---|---|---|---|---|---|
| 查看知识库列表 | 全部 | 有成员关系的 | 所属库 | 所属库 | 所属库 |
| 统一问答 `scope=all` | 全部库 | 有成员关系的库 | 所属库 | 所属库 | 所属库 |
| 创建知识库 | ✅ | ✅ | — | — | ❌ |
| 上传 / 重试解析索引 | 任意库 | 有写权限的库 | ✅ | ✅ | ❌ |
| 查看文档与切片 | 任意库 | 有读权限的库 | ✅ | ✅ | ✅ |
| 管理该库成员 | ✅ | 有写权限的库 | ✅ | ✅ | ❌ |
| 用户管理（建用户/角色/Token） | ✅ | ❌ | ❌ | ❌ | ❌ |

保护规则：不能降低或停用**当前登录的管理员自己**（409）；系统至少保留一个启用状态的管理员（409）；
知识库至少保留一个 `owner`（409）；显式请求未授权知识库返回 403 而非空结果。

## 3. 前端行为

- 启动时调用 `GET /auth/me`：
  - `AUTH_MODE=off` → 返回 `local=true` 的本地管理员，**跳过登录界面**，与历史使用方式一致；
  - `enforced` 且无有效 Token → 401，显示登录覆盖层。
- 登录只接受 **API Token**（P0 已就绪的最短闭环），存入 `localStorage`，请求自动带 `Authorization`；
  任意请求返回 401 会立即回到登录界面。用户名+密码登录留在 P1.5。
- 侧边栏显示当前身份与角色；`me.local` 为真时不显示「退出登录」。
- 按角色呈现：非 `editor/admin` 隐藏建库与上传入口；无库写权限隐藏上传、重试与「成员权限」；
  非 admin 不显示「用户管理」。
- 用户管理面板：创建用户、逐行改角色、启停、签发 Token（**只在签发时显示一次**）、吊销全部 Token。
- 成员权限面板：按邮箱授予 `viewer/editor/owner`、查看成员、移除。

## 4. 验证

- `ruff check .` 通过；`pytest` **104 项通过**（P0 的 90 项 + 本阶段 14 项）；前端生产构建通过。
- 临时 8011 端口以 `AUTH_MODE=enforced` 起真实服务，对真实 MySQL 跑完整链路 **26 项断言全部通过**：
  无 Token → 401；`/auth/me` 角色与 `can_author` 正确；viewer 不能列用户（403）；
  管理员建用户并当场用新 Token 认证成功；改角色生效；停用后原 Token → 401；
  管理员不能降级自己（409）；授权成员后 viewer 的 `scope="all"` 只命中被授权的 kb 10、访问 kb 11 → 403、
  上传 → 403、读成员表 → 403；管理员读成员表 → 200；移除成员 → 204 且重复移除 → 404；
  吊销 Token 后该 Token → 401；管理员仍可见全部 12 个库。
- 验证用的临时用户与 Token 已全部删除（`users`/`api_tokens`/`kb_members` 均为 0 行），临时服务已关闭。
- 界面侧：`/ui/` 返回 200，且服务端实际提供的是本次构建产物（`index-BAKO04fk.js` / `index-YmzOlaPZ.css`），
  产物中包含「登录 KnowOps」「用户管理」「成员权限」「未启用鉴权模式」等 P1 文案与 `/auth/me`、`/admin/users` 调用。
- **未做视觉验收**：本机 Chrome headless 在此沙箱下 GPU 进程崩溃（`GPU process isn't usable`）、
  且沙箱拒绝其写入用户目录，无法截图。因此以上仅为接口与静态产物验证，不等于人工浏览器视觉验收；建议你打开
  <http://127.0.0.1:8010/ui/> 亲自确认一次布局与交互。

## 5. 启用步骤（生产口径）

```bash
cd outputs/knowops
/opt/anaconda3/envs/knowops/bin/alembic upgrade head          # P0 的 0004（本阶段无新迁移）
/opt/anaconda3/envs/knowops/bin/python scripts/manage_users.py \
  create-user --email admin@corp --role admin --token          # 首个管理员，Token 只显示一次
# 之后可在界面上「用户管理」中建用户、签发 Token，在「成员权限」中授权知识库
echo 'AUTH_MODE=enforced' >> .env && 重启 API
```

注意：本地评测脚本（`scripts/evaluate_*.py`、`scripts/check_*.py`）目前不带 Token，切到 `enforced`
前需要为它们配置 Token，否则会收到 401。

## 6. 未做（P2/P3）

- 用户名+密码登录与找回（P1.5）；Token 过期时间与登录限流。
- 提交→审核→发布流程、审计日志、文档版本更新与下架同步（P2）。
- SSO/OIDC、多租户、按部门继承授权（P3）。
- 前端仍为单文件组件，未拆分；未加前端自动化测试。
