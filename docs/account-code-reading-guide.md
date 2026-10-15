# 注册、登录与多用户管理代码阅读索引

建议按“入口 → 业务规则 → 数据与凭据 → 前端”阅读。本次在关键位置补充中文注释，解释设计原因；没有修改运行逻辑。

| 文件 / 函数 | 关注点 |
|---|---|
| `app/modules/auth/router.py` / `RegisterIn`、`register` | 请求校验、禁止客户端指定权限、密码确认、注册模式限制 |
| `app/modules/auth/accounts.py` / `register` | 独立演示空间、租户管理员与平台管理员的区别、限流、并发邮箱唯一约束、事务回滚 |
| `app/modules/auth/service.py` / `authenticate_password` | 密码验证、账号锁定、IP 限流、TOTP 与成功登录后的计数清理 |
| `app/modules/auth/service.py` / `resolve_principal` | 从 Bearer Token 摘要查身份，检查吊销、过期和账号启用状态 |
| `app/modules/auth/router.py` / `list_users` | 先做 SQL 租户限制，再搜索、筛选和分页 |
| `app/modules/auth/accounts.py` / `update` | 锁定管理员记录、验证最终状态、保护最后一个管理员、空间转移、吊销旧会话、提交审计 |
| `app/modules/auth/service.py` / `set_password` | 密码摘要、密码历史、密码变化后的会话失效 |
| `frontend/src/App.vue` / `registerAccount`、`passwordLogin` | 注册后返回登录，取得 Token 后获取后端身份 |
| `frontend/src/App.vue` / `loadUsers`、`resetUserPassword`、`clearAccountSecrets` | 用户列表请求、密码确认、退出与过期时清除敏感表单 |

## 四条流程

1. 注册：表单 → `POST /auth/register` → 校验 → 创建独立租户和账号 → 提交审计 → 返回登录。
2. 登录：`POST /auth/password/login` → 验证密码及可选 TOTP → 签发 Token → `GET /auth/me` → 按身份展示界面。
3. 管理：管理员请求 → 校验目标账号所属空间 → 锁定与验证 → 修改状态和权限 → 吊销旧会话 → 与审计一起提交。
4. 重置密码：管理员确认新密码 → `/admin/users/{id}/password` → 验证密码策略 → 更新摘要并吊销 Token → 成员重新登录。

前端隐藏按钮只改善交互，不构成权限保护；真正的角色、租户和账号状态判断必须在后端执行。账号修改中的事务原子性也不代表项目所有账号操作均使用同一个事务：例如既有密码历史与密码设置路径包含单独提交，需按具体函数阅读。

功能边界和验收见 [开放注册与用户管理说明](public-registration-users.md)。
