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
from app.modules.auth import service
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.knowledge.models import KnowledgeBase


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
    create.add_argument("--token", action="store_true", help="创建后立即签发一个 API token")

    token = sub.add_parser("issue-token", help="为已有用户签发新的 API token")
    token.add_argument("--email", required=True)
    token.add_argument("--label", default="")

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
    if args.command == "create-user":
        user = service.create_user(db, args.email, args.role, args.display_name)
        print(f"已创建用户 id={user.id} email={user.email} role={user.role}")
        if args.token:
            print_token(service.issue_token(db, user, "cli"))
    elif args.command == "issue-token":
        user = require_user(db, args.email)
        print_token(service.issue_token(db, user, args.label))
    elif args.command == "revoke-tokens":
        user = require_user(db, args.email)
        print(f"已吊销 {service.revoke_tokens(db, user)} 个 token")
    elif args.command == "set-role":
        user = require_user(db, args.email)
        user = service.set_user_role(db, user, args.role)
        print(f"用户 {user.email} 角色已改为 {user.role}")
    elif args.command == "grant-kb":
        user = require_user(db, args.email)
        kb = db.get(KnowledgeBase, args.kb_id)
        if kb is None:
            raise SystemExit(f"知识库不存在：{args.kb_id}")
        member = service.ensure_membership(db, kb.id, user.id, args.role)
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
                f"tokens={live} kbs={','.join(memberships) or '-'}"
            )


def main() -> None:
    args = build_parser().parse_args()
    with SessionLocal() as db:
        run(db, args)


if __name__ == "__main__":
    main()
