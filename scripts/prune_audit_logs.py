"""审计日志保留策略：按天数清理旧记录。

默认只统计，加 `--delete` 才真正删除。审计时间戳由 API 进程时钟写入，
这里的截止时间同样用 API 时钟计算，避免与数据库时钟（容器内 UTC）混用。

用法：
    python scripts/prune_audit_logs.py --days 180
    python scripts/prune_audit_logs.py --days 180 --delete
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.modules.audit import service as audit
from app.modules.audit.models import AuditLog


def main() -> None:
    parser = argparse.ArgumentParser(description="按保留天数清理审计日志")
    parser.add_argument("--days", type=int, default=180, help="保留天数（默认 180）")
    parser.add_argument("--delete", action="store_true", help="真正删除（默认只统计）")
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days 必须 >= 1")

    cutoff = datetime.now() - timedelta(days=args.days)
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
        expired = (
            db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff)
            )
            or 0
        )
        print(f"审计共 {total} 条；{cutoff.date()} 之前 {expired} 条（保留 {args.days} 天）")
        if not args.delete:
            if expired:
                print("（默认只统计；确认后加 --delete）")
            return
        print(f"已删除 {audit.prune(db, cutoff)} 条")


if __name__ == "__main__":
    main()
