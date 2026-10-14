"""User, token and knowledge-base membership administration (P0).

Run against the configured MySQL database, after `alembic upgrade head`:

    python scripts/manage_users.py create-user --email admin@corp --role admin --token
    python scripts/manage_users.py grant-kb --email alice@corp --kb-id 10 --role viewer
    python scripts/manage_users.py list-users

Raw tokens are printed once and never stored; only their SHA-256 digest is kept.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.modules.audit import service as audit
from app.modules.auth import service
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.knowledge.models import KnowledgeBase
from app.modules.tenant import service as tenants


class CliActor:
    """The CLI acts outside HTTP, but its changes must still be auditable."""

    id = None
    email = "cli@localhost"
    tenant_id = None


CLI_ACTOR = CliActor()


def find_user(db, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def require_user(db, email: str) -> User:
    user = find_user(db, email)
    if user is None:
        raise SystemExit(f"用户不存在：{email}")
    return user


def print_token(raw: str) -> None:
    print("API token（仅显示一次，请立即保存；不要提交到 Git）：")
    print(f"  {raw}")
    print(f"  请求头：Authorization: Bearer {raw}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KnowOps 用户与授权管理")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="创建用户，可同时签发 token")
    create.add_argument("--email", required=True)
    create.add_argument("--role", choices=["admin", "editor", "viewer"], default="viewer")
    create.add_argument("--display-name", default="")
    create.add_argument("--tenant", default="", help="租户标识；默认使用 default 租户")
    create.add_argument(
        "--platform",
        action="store_true",
        help="平台级账号（tenant 为空，可跨租户管理）；谨慎使用",
    )
    create.add_argument("--password", default="", help="同时设置本地登录密码")
    create.add_argument(
        "--token-days",
        type=int,
        default=None,
        help="token 有效天数；缺省用 TOKEN_TTL_DAYS，0 表示不过期",
    )
    create.add_argument("--token", action="store_true", help="创建后立即签发一个 API token")

    tenant = sub.add_parser("create-tenant", help="创建租户")
    tenant.add_argument("--name", required=True)
    tenant.add_argument("--slug", required=True)

    token = sub.add_parser("issue-token", help="为已有用户签发新的 API token")
    token.add_argument("--email", required=True)
    token.add_argument("--label", default="")
    token.add_argument("--days", type=int, default=None, help="有效天数；0 表示不过期")

    password = sub.add_parser("set-password", help="设置或重置本地登录密码")
    password.add_argument("--email", required=True)
    password.add_argument("--password", required=True)

    revoke = sub.add_parser("revoke-tokens", help="吊销某用户的全部 token")
    revoke.add_argument("--email", required=True)

    role = sub.add_parser("set-role", help="修改用户全局角色")
    role.add_argument("--email", required=True)
    role.add_argument("--role", choices=["admin", "editor", "viewer"], required=True)

    grant = sub.add_parser("grant-kb", help="授予或调整知识库成员角色")
    grant.add_argument("--email", required=True)
    grant.add_argument("--kb-id", type=int, required=True)
    grant.add_argument("--role", choices=["owner", "editor", "viewer"], default="viewer")

    sub.add_parser("list-users", help="列出用户、token 数与知识库成员关系")
    return parser


def run(db, args) -> None:
    if args.command == "create-tenant":
        tenant = tenants.create_tenant(db, args.name, args.slug)
        audit.record(db, CLI_ACTOR, "tenant.create", "tenant", tenant.id, f"slug={tenant.slug}")
        print(f"已创建租户 id={tenant.id} slug={tenant.slug} name={tenant.name}")
    elif args.command == "create-user":
        if args.platform:
            tenant_id = None
        elif args.tenant:
            tenant_id = tenants.get_tenant_by_slug(db, args.tenant).id
        else:
            fallback = tenants.default_tenant(db)
            tenant_id = fallback.id if fallback else None
        if tenant_id is None and not args.platform:
            raise SystemExit("没有可用租户，请先 create-tenant，或使用 --platform 创建平台账号")
        user = service.create_user(db, args.email, args.role, args.display_name, tenant_id)
        audit.record(
            db, CLI_ACTOR, "user.create", "user", user.id, f"role={user.role} tenant={tenant_id}"
        )
        scope = "平台级" if tenant_id is None else f"租户 {tenant_id}"
        print(f"已创建用户 id={user.id} email={user.email} role={user.role} {scope}")
        if args.password:
            service.set_password(db, user, args.password, actor=CLI_ACTOR)
            print("已设置本地登录密码")
        if args.token:
            print_token(service.issue_token(db, user, "cli", args.token_days))
            audit.record(db, CLI_ACTOR, "token.issue", "user", user.id, "label=cli")
    elif args.command == "issue-token":
        user = require_user(db, args.email)
        print_token(service.issue_token(db, user, args.label, args.days))
        audit.record(db, CLI_ACTOR, "token.issue", "user", user.id, f"label={args.label}"[:512])
    elif args.command == "set-password":
        user = require_user(db, args.email)
        service.set_password(db, user, args.password, actor=CLI_ACTOR)
        print(f"已为 {user.email} 设置本地登录密码")
    elif args.command == "revoke-tokens":
        user = require_user(db, args.email)
        count = service.revoke_tokens(db, user)
        audit.record(db, CLI_ACTOR, "token.revoke", "user", user.id, f"revoked={count}")
        print(f"已吊销 {count} 个 token")
    elif args.command == "set-role":
        user = require_user(db, args.email)
        user = service.set_user_role(db, user, args.role)
        audit.record(db, CLI_ACTOR, "user.update", "user", user.id, f"role={user.role}")
        print(f"用户 {user.email} 角色已改为 {user.role}")
    elif args.command == "grant-kb":
        user = require_user(db, args.email)
        kb = db.get(KnowledgeBase, args.kb_id)
        if kb is None:
            raise SystemExit(f"知识库不存在：{args.kb_id}")
        member = service.ensure_membership(db, kb.id, user.id, args.role)
        audit.record(
            db,
            CLI_ACTOR,
            "kb.member.grant",
            "knowledge_base",
            kb.id,
            f"user={user.email} role={member.role}",
        )
        print(f"已授予 {user.email} 对知识库 {kb.id}({kb.name}) 的 {member.role} 权限")
    elif args.command == "list-users":
        for user in db.scalars(select(User).order_by(User.id)):
            memberships = [
                f"{member.kb_id}:{member.role}"
                for member in db.scalars(
                    select(KbMember).where(KbMember.user_id == user.id).order_by(KbMember.kb_id)
                )
            ]
            live = db.scalar(
                select(func.count())
                .select_from(ApiToken)
                .where(ApiToken.user_id == user.id, ApiToken.revoked_at.is_(None))
            )
            print(
                f"id={user.id} {user.email} role={user.role} active={user.is_active} "
                f"tenant={user.tenant_id if user.tenant_id is not None else 'platform'} "
                f"tokens={live} kbs={','.join(memberships) or '-'}"
            )


def main() -> None:
    args = build_parser().parse_args()
    with SessionLocal() as db:
        run(db, args)


if __name__ == "__main__":
    main()
